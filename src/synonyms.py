"""src/synonyms.py -- словарь синонимов с весами релевантности.

Формат data/synonyms.json:
  {"ключ": [{"word": "инструмент", "weight": 0.8}, ...]}

weight в файле -- вес релевантности (для отбора топ-N). Не путать
с весом при векторизации (0.1/M) -- он вычисляется в preprocess.py.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("ai_terminator.synonyms")


class SynonymDict:
    """Загружает словарь синонимов из JSON-файла.

    Если файл отсутствует или невалиден, система работает с пустым словарём.

    Пример:
        sd = SynonymDict(json_path='data/synonyms.json')
        sd.get_synonyms('ключ')          # -> ['инструмент', 'отмычка']
        sd.get_synonyms('ключ', max_synonyms=1)  # -> ['инструмент']
    """

    def __init__(self, json_path: str | Path) -> None:
        self._data: dict[str, list[dict]] = {}
        path_str = str(json_path)

        try:
            with open(path_str, encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            logger.warning("Файл синонимов не найден: %s. Работа без синонимов.", path_str)
            return
        except json.JSONDecodeError as exc:
            logger.error("Ошибка парсинга %s: %s. Работа без синонимов.", path_str, exc)
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("Непредвиденная ошибка при загрузке %s: %s", path_str, exc)
            return

        if not isinstance(raw, dict):
            logger.error(
                "Неверный формат: корень должен быть словарём, получен %s",
                type(raw).__name__,
            )
            return

        validated: dict[str, list[dict]] = {}
        for key, entries in raw.items():
            if not isinstance(entries, list):
                logger.error(
                    "Статья %r: значение должно быть списком, получен %s. Пропущена.",
                    key,
                    type(entries).__name__,
                )
                self._data = {}
                return
            clean_entries = []
            for item in entries:
                if not isinstance(item, dict):
                    logger.error(
                        "Статья %r: элемент должен быть словарём, получен %s. Пропущен.",
                        key,
                        type(item).__name__,
                    )
                    self._data = {}
                    return
                word = item.get("word", "")
                if not word or not str(word).strip():
                    logger.warning("Статья %r: пустое поле 'word'. Пропущено.", key)
                    continue
                weight = item.get("weight", 0.5)
                if not isinstance(weight, (int, float)):
                    weight = 0.5
                clean_entries.append({"word": str(word), "weight": float(weight)})
            validated[key] = clean_entries

        self._data = validated
        logger.info("Загружено %d словарных статей из %s", len(self._data), path_str)

    def get_synonyms(self, lemma: str, max_synonyms: int = 2) -> list[str]:
        """Вернуть топ-N синонимов для леммы по убыванию веса.

        Args:
            lemma:        лемма слова (нормальная форма).
            max_synonyms: максимальное количество синонимов.

        Returns:
            Список слов-синонимов, отсортированных по убыванию веса релевантности.
        """
        entries = self._data.get(lemma, [])
        if not entries:
            return []
        sorted_entries = sorted(entries, key=lambda e: e["weight"], reverse=True)
        return [e["word"] for e in sorted_entries[:max_synonyms]]

    def has_synonyms(self, lemma: str) -> bool:
        """Вернуть True если для леммы есть хотя бы один синоним."""
        return bool(self._data.get(lemma))
