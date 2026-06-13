import pytest
from pathlib import Path
from src.config import Config
from src.lemmatizer import Lemmatizer
from src.preprocess import preprocess_base

PROJECT_ROOT = Path(__file__).parent.parent

@pytest.fixture(autouse=True)
def reset_singleton():
    Lemmatizer._instance = None
    yield
    Lemmatizer._instance = None

@pytest.fixture
def cfg():
    return Config.from_json("configs/config.json", project_root=PROJECT_ROOT)

@pytest.fixture
def lm():
    return Lemmatizer()

def test_basic(cfg, lm):
    r = preprocess_base("\u041a\u043b\u044e\u0447!", ["\u0422\u0435\u0445\u043d\u0438\u043a\u0430", "\u0422\u0435\u0445\u043d\u0438\u043a\u0430"], cfg, lm)
    assert r["status"] == "ok"
    assert r["term_lemmas"] == ["\u043a\u043b\u044e\u0447"]
    assert r["clean_hints"] == ["\u0442\u0435\u0445\u043d\u0438\u043a\u0430"]
    assert any("\u0434\u0443\u0431\u043b" in w for w in r["warnings"])

def test_empty_term(cfg, lm):
    r = preprocess_base("!!!", [], cfg, lm)
    assert r["status"] == "error"

def test_long_term(cfg, lm):
    r = preprocess_base("\u043a" * 200, [], cfg, lm)
    assert r["status"] == "error"
    assert "\u0434\u043b\u0438\u043d\u043d" in r["message"]

def test_none_hints(cfg, lm):
    r = preprocess_base("\u043a\u043b\u044e\u0447", None, cfg, lm)
    assert r["status"] == "ok"
    assert r["hints_lemmas"] == []