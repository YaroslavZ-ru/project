import logging
from collections import OrderedDict
from pathlib import Path
import numpy as np

logger = logging.getLogger('ai_terminator.embeddings')


class FastTextWrapper:
    def __init__(self, model_path, fallback_path, cache_size):
        self._model_path = Path(model_path)
        self._fallback_path = Path(fallback_path) if fallback_path else None
        self._cache_maxsize = cache_size
        self._model = None
        self._fallback = None
        self._model_loaded = False
        self._fallback_loaded = False
        self._dim = 300
        self._word_cache = OrderedDict()
        self._warned_words = set()

    def _load_fallback(self):
        if self._fallback_loaded:
            return
        self._fallback_loaded = True
        if self._fallback_path is None or not self._fallback_path.exists():
            logger.warning('Fallback-файл не задан или не найден: %s', self._fallback_path)
            return
        try:
            data = np.load(str(self._fallback_path), allow_pickle=True).item()
            if not isinstance(data, dict) or not data:
                logger.warning('Неверный формат fallback-файла.')
                return
            first_vec = next(iter(data.values()))
            self._dim = len(first_vec)
            self._fallback = data
            logger.info('Fallback загружен: %d слов, размерность %d', len(data), self._dim)
        except Exception as exc:
            logger.error('Ошибка загрузки fallback: %s', exc)

    def _ensure_model(self):
        if self._model_loaded:
            return
        self._model_loaded = True
        if self._model_path.exists():
            try:
                import fasttext
                self._model = fasttext.load_model(str(self._model_path))
                self._dim = len(self._model.get_word_vector('а'))
                logger.info('FastText загружена, размерность %d', self._dim)
            except Exception as exc:
                logger.error('Ошибка загрузки fastText: %s', exc)
                self._load_fallback()
        else:
            logger.error('Файл модели не найден: %s', self._model_path)
            self._load_fallback()
        if self._model is None and self._fallback is None:
            logger.warning('Ни fastText, ни fallback не загружены. Все векторы будут нулевыми.')

    def get_word_vector(self, word):
        word = word.lower().strip()
        if not word:
            return np.zeros(self._dim, dtype=np.float32)
        self._ensure_model()
        if word in self._word_cache:
            self._word_cache.move_to_end(word)
            return self._word_cache[word]
        vec = None
        if self._model is not None:
            try:
                vec = np.array(self._model.get_word_vector(word), dtype=np.float32)
            except Exception as exc:
                logger.warning('Ошибка get_word_vector(%r): %s', word, exc)
        if vec is None and self._fallback is not None:
            raw = self._fallback.get(word)
            vec = np.array(raw, dtype=np.float32) if raw is not None else np.zeros(self._dim, dtype=np.float32)
        if vec is None:
            vec = np.zeros(self._dim, dtype=np.float32)
            if word not in self._warned_words:
                logger.warning('Модель недоступна, нулевой вектор для: %r', word)
                self._warned_words.add(word)
        if len(self._word_cache) >= self._cache_maxsize:
            self._word_cache.popitem(last=False)
        self._word_cache[word] = vec
        return vec

    def get_phrase_vector(self, phrase):
        words = [w for w in phrase.split() if w]
        if not words:
            return np.zeros(self._dim, dtype=np.float32)
        vecs = [self.get_word_vector(w) for w in words]
        return np.mean(vecs, axis=0).astype(np.float32)

    def get_dimension(self):
        self._ensure_model()
        return self._dim