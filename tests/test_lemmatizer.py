import pytest
from src.lemmatizer import Lemmatizer


@pytest.fixture(autouse=True)
def reset_singleton():
    Lemmatizer._instance = None
    yield
    Lemmatizer._instance = None


def test_basic_word():
    lm = Lemmatizer()
    assert lm.lemmatize_word("ключи") == "ключ"

def test_empty_word():
    lm = Lemmatizer()
    assert lm.lemmatize_word("") == ""

def test_phrase_with_hyphen():
    lm = Lemmatizer()
    assert lm.lemmatize_phrase("ключ-гаечный") == ["ключ", "гаечный"]

def test_empty_phrase():
    lm = Lemmatizer()
    assert lm.lemmatize_phrase("") == []

def test_singleton():
    lm1 = Lemmatizer()
    lm2 = Lemmatizer()
    assert lm1 is lm2

def test_cache_works():
    lm = Lemmatizer()
    r1 = lm.lemmatize_word("ключ")
    r2 = lm.lemmatize_word("ключ")
    assert r1 == r2
    assert "ключ" in lm._cache

def test_lru_eviction():
    lm = Lemmatizer(cache_size=2)
    lm.lemmatize_word("ключ")
    lm.lemmatize_word("винт")
    lm.lemmatize_word("гайка")
    assert len(lm._cache) == 2