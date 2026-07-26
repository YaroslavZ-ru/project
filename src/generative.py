"""src/generative.py -- генеративное расширение параметров AI-Terminator.

Модуль полностью опциональный: если use_generative=False или transformers
не установлен -- expand() молча возвращает [].
Никогда не бросает исключений наружу -- все ошибки логируются.
"""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
import logging
import re

from src.config import Config
from src.utils import safe_truncate

logger = logging.getLogger(__name__)

# Опциональная зависимость -- transformers
_TRANSFORMERS_AVAILABLE = True
try:
    from transformers import pipeline as hf_pipeline  # type: ignore
except ImportError:
    _TRANSFORMERS_AVAILABLE = False


class GenerativeExpander:
    """Расширяет список параметров с помощью LLM, когда база знаний
    вернула недостаточно параметров.

    Полностью опциональный: при use_generative=False или
    отсутствии transformers -- expand() возвращает [].

    Attributes:
        _cfg:          конфигурация проекта.
        _pipe:         HuggingFace pipeline (ленивая загрузка).
        _model_loaded: флаг попытки загрузки.
        _available:    флаг доступности модуля.
    """

    def __init__(self, config: Config) -> None:
        """Args:
        config: конфигурация AI-Terminator.
        """
        self._cfg = config
        self._pipe = None
        self._model_loaded = False
        self._available = _TRANSFORMERS_AVAILABLE and config.use_generative

        if not _TRANSFORMERS_AVAILABLE:
            logger.warning("transformers не установлен. Генеративный модуль отключён.")
        elif not config.use_generative:
            logger.info("use_generative=False. GenerativeExpander пассивен.")

    def _ensure_pipeline(self) -> None:
        """Ленивая загрузка HuggingFace pipeline.

        Вызывается перед первым generate, но только один раз.
        Если загрузка невозможна -- выставляет _available=False.
        """
        if self._model_loaded:
            return
        self._model_loaded = True

        if not self._available:
            return

        try:
            self._pipe = hf_pipeline(
                "text-generation",
                model=self._cfg.generative_model,
                max_new_tokens=self._cfg.generative_max_new_tokens,
                temperature=self._cfg.generative_temperature,
                do_sample=True,
            )
            logger.info(
                "GenerativeExpander: модель загружена: %s",
                self._cfg.generative_model,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка загрузки генеративной модели: %s", exc)
            self._pipe = None
            self._available = False

    def _build_prompt(
        self,
        term: str,
        hints: list[str],
        existing_params: list[dict],
    ) -> str:
        """Строит промпт для LLM на русском языке.

        Args:
            term:            термин запроса.
            hints:           уточнения.
            existing_params: уже найденные параметры.

        Returns:
            Готовый промпт, усечённый до 512 символов.
        """
        existing_labels = [p.get("label_ru", p.get("name", "")) for p in existing_params[:3]]
        params_str = ", ".join(existing_labels)
        hints_str = ", ".join(hints) if hints else ""
        context = f" {hints_str}" if hints_str else ""
        prompt = (
            f"{term}{context}: {params_str}, "
        )
        return safe_truncate(prompt, 128)

    def _slugify(self, text: str) -> str:
        """Преобразует label_ru в техническое name.

        Args:
            text: человеческое название параметра.

        Returns:
            Slug: нижний регистр, пробелы/дефисы -> '_',
            оставляются только буквы, цифры, '_'.

        Example:
            "Момент затяжки" -> "момент_затяжки"
        """
        text = text.lower()
        text = re.sub(r"[ \-]+", "_", text)
        text = re.sub(r"[^\w]", "", text, flags=re.UNICODE)
        return text

    def _parse_response(
        self,
        response_text: str,
        existing_names: set[str],
        existing_params: list[dict],
    ) -> list[dict]:
        """Парсит ответ LLM и возвращает новые параметры.

        Args:
            response_text:  текст ответа модели.
            existing_names: имена уже существующих параметров.
            existing_params: полный список параметров для проверки дубликатов.

        Returns:
            Список новых параметров (ограничен generative_max_new_params).
        """
        # Берём подстроку после последнего ':'
        colon_pos = response_text.rfind(":")
        text_to_parse = response_text[colon_pos + 1 :] if colon_pos >= 0 else response_text

        # Разбиваем по запятым, точке с запятой, переносам строк, точкам
        candidates_raw = re.split(r"[,;\n.]+", text_to_parse)

        # Стоп-слова для фильтрации предложений
        stop_words = {
            "и", "в", "на", "с", "по", "для", "от", "до", "из", "к", "о", "у",
            "это", "эта", "эти", "этот", "того", "этой", "при", "не", "ни",
            "которые", "который", "которая", "которое", "все", "всех", "всем",
            "быть", "был", "была", "были", "будет", "будут", "является",
            "может", "могут", "нужно", "нужен", "нужна", "нужны",
            "один", "одна", "одно", "два", "три", "четыре", "пять",
            "более", "менее", "очень", "также", "кроме", "помимо",
            "часть", "некоторые", "другие", "другой", "другая", "другое",
            "как", "так", "его", "её", "их", "ему", "ей", "им",
            "где", "когда", "почему", "зачем", "сколько", "какой", "какая", "какое",
            "свой", "своя", "своё", "свои", "мой", "моя", "моё", "мои",
            "наш", "наша", "наше", "наши", "ваш", "ваша", "ваше", "ваши",
            "сам", "сама", "само", "сами", "самый", "самая", "самое", "самые",
            "весь", "вся", "всё", "все", "каждый", "каждая", "каждое", "каждые",
            "любой", "любая", "любое", "любые", "некий", "некая", "некое", "некие",
            "такой", "такая", "такое", "такие", "столько", "несколько",
            "год", "года", "лет", "месяц", "месяца", "день", "дня", "час", "часа",
            "время", "минута", "минуты", "секунда", "секунды",
            "лицо", "лица", "рука", "руки", "нога", "ноги", "голова", "головы",
            "дело", "дела", "слово", "слова", "место", "места", "сторона", "стороны",
            "вопрос", "вопроса", "ответ", "ответа", "проблема", "проблемы",
            "задача", "задачи", "цель", "цели", "результат", "результата",
            "процесс", "процесса", "система", "системы", "метод", "метода",
            "способ", "способа", "пример", "примера", "вид", "вида",
            "тип", "типа", "форма", "формы", "размер", "размера",
            "материал", "материала", "вещество", "вещества",
            "устройство", "устройства", "прибор", "прибора",
            "машина", "машины", "станок", "станка",
            "работа", "работы", "функция", "функции",
            "процесс", "процесса", "операция", "операции",
            "условие", "условия", "требование", "требования",
            "параметр", "параметра", "характеристика", "характеристики",
            "свойство", "свойства", "показатель", "показателя",
            "значение", "значения", "величина", "величины",
            "уровень", "уровня", "степень", "степени",
            "класс", "класса", "категория", "категории",
            "группа", "группы", "серия", "серии",
            "модель", "модели", "образец", "образца",
            "марка", "марки", "бренд", "бренда",
            "производитель", "производителя", "изготовитель", "изготовителя",
            "страна", "страны", "город", "города",
            "дата", "даты", "срок", "срока",
            "цена", "цены", "стоимость", "стоимости",
            "количество", "количества", "объем", "объема",
            "площадь", "площади", "длина", "длины",
            "ширина", "ширины", "высота", "высоты",
            "глубина", "глубины", "толщина", "толщины",
            "диаметр", "диаметра", "радиус", "радиуса",
            "масса", "массы", "вес", "веса",
            "плотность", "плотности", "вязкость", "вязкости",
            "температура", "температуры", "давление", "давления",
            "напряжение", "напряжения", "ток", "тока",
            "мощность", "мощности", "энергия", "энергии",
            "скорость", "скорости", "ускорение", "ускорения",
            "частота", "частоты", "период", "периода",
            "добротность", "добротности", "коэффициент", "коэффициента",
            "отношение", "отношения", "разница", "разницы",
            "сумма", "суммы", "произведение", "произведения",
            "отношение", "отношения", "дельта", "дельты",
            "погрешность", "погрешности", "точность", "точности",
            "надежность", "надежности", "долговечность", "долговечности",
            "износостойкость", "износостойкости", "прочность", "прочности",
            "жесткость", "жесткости", "устойчивость", "устойчивости",
            "стойкость", "стойкости", "коррозионная", "коррозионной",
            "термостойкость", "термостойкости", "водостойкость", "водостойкости",
            "огнестойкость", "огнестойкости", "химическая", "химической",
            "биологическая", "биологической", "экологическая", "экологической",
            "безопасность", "безопасности", "эксплуатация", "эксплуатации",
            "обслуживание", "обслуживания", "ремонт", "ремонта",
            "установка", "установки", "монтаж", "монтажа",
            "демонтаж", "демонтажа", "транспортировка", "транспортировки",
            "хранение", "хранения", "утилизация", "утилизации",
            "гарантия", "гарантии", "срок", "срока",
            "标准", "标准", "规范", "规范",
        }

        # Ключевые слова для определения типа параметра
        keywords = getattr(self._cfg, "generative_keywords", [])

        result: list[dict] = []
        for raw in candidates_raw:
            candidate = raw.strip().strip("\"'«»()0123456789. ")
            if len(candidate) < 3 or len(candidate) > 60:
                continue

            # Пропускаем мусорные строки
            skip_words = ["выполнение", "команд", "танк", "цели", "случай",
                         "ndash", "nbsp", "mdash", "amp", "quot", "lt", "gt"]
            if any(skip in candidate.lower() for skip in skip_words):
                continue

            # Пропускаем строки с HTML-сущностями
            if "&" in candidate or ";" in candidate:
                continue

            # Пропускаем строки с цифрами в начале (нумерация)
            if candidate and candidate[0].isdigit():
                continue

            # Если кандидат - это предложение (более 4 слов), извлекаем существительные
            words = candidate.split()
            if len(words) > 4:
                # Извлекаем существительные (грубая эвристика: слова длиной > 3, не стоп-слова)
                nouns = [w for w in words if len(w) > 3 and w.lower() not in stop_words]
                if nouns:
                    candidate = " ".join(nouns[:3])  # Берём до 3 слов
                else:
                    continue

            # Пропускаем слишком короткие или слишком длинные
            if len(candidate) < 3 or len(candidate) > 40:
                continue

            # Проверка на ключевые слова (мягкая - любое вхождение)
            has_keyword = any(kw in candidate.lower() for kw in keywords)

            # Определяем тип по ключевым словам
            param_type = "string"
            if any(w in candidate.lower() for w in ["мм", "см", "кг", "г ", "вт", "гац"]):
                param_type = "float"
            elif any(w in candidate.lower() for w in ["есть", "нет", "да", "можно"]):
                param_type = "boolean"

            slug = self._slugify(candidate)
            if not slug or slug in existing_names or len(slug) < 3:
                continue

            # Проверка на семантические дубликаты (рус/англ совпадение)
            candidate_lower = candidate.lower().strip()
            is_duplicate = False
            for ep in existing_params:
                ep_name = ep.get("name", "").lower()
                ep_label = ep.get("label_ru", "").lower()
                # Точное совпадение или вхождение
                if (candidate_lower in ep_label or ep_label in candidate_lower or
                    candidate_lower in ep_name or ep_name in candidate_lower):
                    is_duplicate = True
                    break
                # Совпадение ключевых слов (мм, кг и т.д.)
                if any(w in candidate_lower and w in ep_label for w in ["мм", "кг", "ватт"]):
                    is_duplicate = True
                    break
            if is_duplicate:
                continue

            result.append(
                {
                    "name": slug,
                    "label_ru": candidate.strip().capitalize(),
                    "type": param_type,
                    "description": "Предложено генеративной моделью",
                    "confidence": 0.3,
                    "source": "generative",
                }
            )

            if len(result) >= self._cfg.generative_max_new_params:
                break

        return result

    def expand(
        self,
        term: str,
        hints: list[str],
        existing_params: list[dict],
        cfg: Config | None = None,
    ) -> list[dict]:
        """Расширяет список параметров через LLM.

        Args:
            term:            термин запроса.
            hints:           список уточнений.
            existing_params: уже найденные параметры.
            cfg:             если None -- использует self._cfg.

        Returns:
            Список новых параметров (может быть пустым).
            Все ошибки логируются, наружу не пробрасываются.
        """
        active_cfg = cfg if cfg is not None else self._cfg

        if not self._available:
            return []

        self._ensure_pipeline()

        if self._pipe is None:
            return []

        existing_names = {p.get("name", "") for p in existing_params}
        prompt = self._build_prompt(term, hints, existing_params)

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self._pipe,
                    prompt,
                    max_new_tokens=50,
                    temperature=0.9,
                    do_sample=True,
                    top_k=50,
                    top_p=0.95,
                    repetition_penalty=1.2,
                    num_return_sequences=1,
                )
                try:
                    result = future.result(timeout=active_cfg.generative_timeout_seconds)
                except FuturesTimeoutError:
                    logger.warning(
                        "GenerativeExpander: таймаут (%ss)",
                        active_cfg.generative_timeout_seconds,
                    )
                    return []
                except Exception as exc:  # noqa: BLE001
                    logger.error("GenerativeExpander: ошибка генерации: %s", exc)
                    return []
        except Exception as exc:  # noqa: BLE001
            logger.error("GenerativeExpander: ошибка executor: %s", exc)
            return []

        if not result or not isinstance(result, list):
            logger.warning("GenerativeExpander: пустой ответ модели")
            return []

        first = result[0]
        if not isinstance(first, dict) or "generated_text" not in first:
            logger.warning("GenerativeExpander: неверный формат ответа модели")
            return []

        generated_text = first["generated_text"]
        new_params = self._parse_response(generated_text, existing_names, existing_params)
        logger.info("GenerativeExpander: добавлено %d параметров", len(new_params))
        return new_params
