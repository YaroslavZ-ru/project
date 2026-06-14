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
    r = preprocess_base("Ключ!", ["Техника", "Техника"], cfg, lm)
    assert r["status"] == "ok"
    assert r["term_lemmas"] == ["ключ"]
    assert r["clean_hints"] == ["техника"]
    assert any("дубл" in w for w in r["warnings"])


def test_empty_term(cfg, lm):
    r = preprocess_base("!!!", [], cfg, lm)
    assert r["status"] == "error"


def test_long_term(cfg, lm):
    r = preprocess_base("к" * 200, [], cfg, lm)
    assert r["status"] == "error"
    assert "длинн" in r["message"]


def test_none_hints(cfg, lm):
    r = preprocess_base("ключ", None, cfg, lm)
    assert r["status"] == "ok"
    assert r["hints_lemmas"] == []
