"""src/lemmatizer.py -- синглтон-лемматизатор с LRU-кэшем.

Использует pymorphy3 для приведения слов к начальной форме.\nСоздаётся один раз за всё время работы приложения (синглтон).
Повторные Lemmatizer() возвращают тот же объект, кэш не сбрасывается.
"""
from collections import OrderedDict
import logging

import pymorphy3

logger = logging.getLogger("ai_terminator.lemmatizer")


class Lemmatizer:
    """Синглтон-лемматизатор русского языка с LRU-кэшем.

    Пример:
        lemmatizer = Lemmatizer(cache_size=1000)
        lemmatizer.lemmatize_word('ключи')     # -> 'ключ'
        lemmatizer.lemmatize_phrase('ключ-гаечный')  # -> ['ключ', 'гаечный']
    """

    _instance: "Lemmatizer | None" = None
    # Аннотации атрибутов экземпляра (задаются в __new__)
    _morph: "pymorphy3.MorphAnalyzer"
    _cache: "OrderedDict[str, str]"
    _cache_size: int

    def __new__(cls, cache_size: int = 1000) -> "Lemmatizer":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._morph = pymorphy3.MorphAnalyzer()
            instance._cache: OrderedDict[str, str] = OrderedDict()
            instance._cache_size = cache_size
            cls._instance = instance
            logger.info("Lemmatizer инициализирован (cache_size=%d)", cache_size)
        return cls._instance

    # ------------------------------------------------------------------
    def lemmatize_word(self, word: str) -> str:
        """Привести одно слово к начальной форме (лемме).

        Args:
            word: одно слово без пробелов и дефисов.

        Returns:
            Лемма слова или word.lower() если парсинг невозможен.
        """
        if not word:
            return ""

        # Проверяем кэш
        if word in self._cache:
            self._cache.move_to_end(word)
            logger.debug("Кэш-попадание: %r", word)
            return self._cache[word]

        # Кэш-промах: лемматизируем
        try:
            parses = self._morph.parse(word)
            if parses:
                best = max(parses, key=lambda p: p.score)
                lemma = best.normal_form
            else:
                lemma = word.lower()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ошибка лемматизации %r: %s", word, exc)
            lemma = word.lower()

        # Добавляем в LRU-кэш
        if len(self._cache) >= self._cache_size:
            self._cache.popitem(last=False)
        self._cache[word] = lemma
        logger.debug("Лемматизация: %r -> %r", word, lemma)
        return lemma

    def lemmatize_phrase(self, phrase: str) -> list[str]:
        """Разбить фразу на слова и лемматизировать каждое.

        Дефисы заменяются пробелами перед разбиением.

        Args:
            phrase: строка, может содержать пробелы и/или дефисы.

        Returns:
            Список лемм каждого слова, пустые строки отбрасываются.
        """
        if not phrase:
            return []
        phrase = phrase.replace("-", " ")
        return [
            lemma
            for w in phrase.split()
            if w
            for lemma in [self.lemmatize_word(w)]
            if lemma
        ]