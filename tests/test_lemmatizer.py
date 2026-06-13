import pytest
from src.lemmatizer import Lemmatizer


@pytest.fixture(autouse=True)
def reset_singleton():
    Lemmatizer._instance = None
    yield
    Lemmatizer._instance = None


def test_basic_word():
    lm = Lemmatizer()
    assert lm.lemmatize_word("\u043a\u043b\u044e\u0447\u0438") == "\u043a\u043b\u044e\u0447"

def test_empty_word():
    lm = Lemmatizer()
    assert lm.lemmatize_word("") == ""

def test_phrase_with_hyphen():
    lm = Lemmatizer()
    assert lm.lemmatize_phrase("\u043a\u043b\u044e\u0447-\u0433\u0430\u0435\u0447\u043d\u044b\u0439") == ["\u043a\u043b\u044e\u0447", "\u0433\u0430\u0435\u0447\u043d\u044b\u0439"]

def test_empty_phrase():
    lm = Lemmatizer()
    assert lm.lemmatize_phrase("") == []

def test_singleton():
    lm1 = Lemmatizer()
    lm2 = Lemmatizer()
    assert lm1 is lm2

def test_cache_works():
    lm = Lemmatizer()
    r1 = lm.lemmatize_word("\u043a\u043b\u044e\u0447")
    r2 = lm.lemmatize_word("\u043a\u043b\u044e\u0447")
    assert r1 == r2
    assert "\u043a\u043b\u044e\u0447" in lm._cache

def test_lru_eviction():
    lm = Lemmatizer(cache_size=2)
    lm.lemmatize_word("\u043a\u043b\u044e\u0447")
    lm.lemmatize_word("\u0432\u0438\u043d\u0442")
    lm.lemmatize_word("\u0433\u0430\u0439\u043a\u0430")
    assert len(lm._cache) == 2