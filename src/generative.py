"""src/generative.py -- генеративное расширение параметров AI-Terminator.

Модуль полностью опциональный: если use_generative=False или transformers
не установлен -- expand() молча возвращает [].
Никогда не бросает исключений наружу -- все ошибки логируются.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

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
        params_str = ", ".join(
            p.get("label_ru", p.get("name", "")) for p in existing_params
        )
        hints_str = ", ".join(hints) if hints else "нет"
        prompt = (
            f"Термин: {term}\n"
            f"Уточнения: {hints_str}\n"
            f"Существующие параметры: {params_str}\n"
            f"Предложи дополнительные характеристики через запятую:"
        )
        return safe_truncate(prompt, 512)

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
    ) -> list[dict]:
        """Парсит ответ LLM и возвращает новые параметры.

        Args:
            response_text:  текст ответа модели.
            existing_names: имена уже существующих параметров.

        Returns:
            Список новых параметров (ограничен generative_max_new_params).
        """
        # Берём подстроку после последнего ':'
        colon_pos = response_text.rfind(":")
        text_to_parse = (
            response_text[colon_pos + 1 :] if colon_pos >= 0 else response_text
        )

        # Разбиваем по запятым, точке с запятой, переносам строк
        candidates_raw = re.split(r"[,;\n]", text_to_parse)

        result: list[dict] = []
        for raw in candidates_raw:
            candidate = raw.strip().strip("\"'«»()")
            if len(candidate) < 2 or len(candidate) > 80:
                continue

            # Проверка на ключевые слова
            keywords = getattr(self._cfg, "generative_keywords", [])
            if not any(kw in candidate.lower() for kw in keywords):
                continue

            slug = self._slugify(candidate)
            if slug in existing_names:
                continue

            result.append(
                {
                    "name": slug,
                    "label_ru": candidate.strip(),
                    "type": "string",
                    "description": "Предложено генеративной моделью",
                    "confidence": 0.2,
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
                future = executor.submit(self._pipe, prompt)
                try:
                    result = future.result(
                        timeout=active_cfg.generative_timeout_seconds
                    )
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
        new_params = self._parse_response(generated_text, existing_names)
        logger.info("GenerativeExpander: добавлено %d параметров", len(new_params))
        return new_params
