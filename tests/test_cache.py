import numpy as np
import pytest

from src.cache import QueryVectorCache


class CfgMock:
    use_synonyms = True
    max_synonyms_per_token = 2


@pytest.fixture
def cfg():
    return CfgMock()


@pytest.fixture
def cache():
    return QueryVectorCache(maxsize=10)


def test_put_and_get(cache, cfg):
    vec = np.array([0.1] * 300, dtype=np.float32)
    cache.put("ключ", ["техника"], cfg, vec)
    assert np.allclose(cache.get("ключ", ["техника"], cfg), vec)


def test_hints_order_independent(cache, cfg):
    vec = np.array([0.5] * 300, dtype=np.float32)
    cache.put("ключ", ["техника", "вращение"], cfg, vec)
    assert np.allclose(cache.get("ключ", ["вращение", "техника"], cfg), vec)


def test_different_synonyms_flag_is_miss(cache):
    vec = np.zeros(300, dtype=np.float32)
    c1 = CfgMock()
    c1.use_synonyms = True
    c2 = CfgMock()
    c2.use_synonyms = False
    cache.put("ключ", [], c1, vec)
    assert cache.get("ключ", [], c2) is None


def test_lru_eviction(cfg):
    c = QueryVectorCache(maxsize=2)
    v = np.zeros(300, dtype=np.float32)
    c.put("а", [], cfg, v)
    c.put("б", [], cfg, v)
    c.put("в", [], cfg, v)
    assert c.get("а", [], cfg) is None


def test_clear(cache, cfg):
    cache.put("ключ", [], cfg, np.zeros(300, dtype=np.float32))
    cache.clear()
    assert cache.get("ключ", [], cfg) is None
