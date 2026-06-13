import logging
from collections import OrderedDict
import numpy as np

logger = logging.getLogger('ai_terminator.cache')


class QueryVectorCache:
    def __init__(self, maxsize=100):
        self._cache = OrderedDict()
        self._maxsize = maxsize

    def _build_key(self, term, hints, config):
        return (
            term.lower().strip(),
            tuple(sorted(h.lower().strip() for h in hints)),
            config.use_synonyms,
            config.max_synonyms_per_token,
        )

    def get(self, term, hints, config):
        key = self._build_key(term, hints, config)
        if key not in self._cache:
            logger.debug('cache miss: %r', term)
            return None
        self._cache.move_to_end(key)
        logger.debug('cache hit: %r', term)
        return np.array(self._cache[key], dtype=np.float32)

    def put(self, term, hints, config, vector):
        key = self._build_key(term, hints, config)
        if len(self._cache) >= self._maxsize:
            self._cache.popitem(last=False)
        self._cache[key] = tuple(vector.tolist())
        logger.debug('cache store: %r', term)

    def clear(self):
        self._cache.clear()
        logger.info('QueryVectorCache очищен')