import pytest
from pathlib import Path
from src.config import Config
from src.lemmatizer import Lemmatizer
from src.fallback import detect_domain, fallback_response, load_json_config

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def reset_lem():
    Lemmatizer._instance = None
    yield
    Lemmatizer._instance = None


@pytest.fixture
def cfg():
    return Config.from_json("configs/config.json", project_root=PROJECT_ROOT)


def test_detect_domain_music():
    all_lemmas = {"скрипичный", "нотный"}
    result = detect_domain(
        all_lemmas, str(PROJECT_ROOT / "configs" / "domain_keywords.json")
    )
    assert result == "музыка"


def test_detect_domain_no_match():
    result = detect_domain(
        {"хмурыкало"}, str(PROJECT_ROOT / "configs" / "domain_keywords.json")
    )
    assert result == "общее"


def test_fallback_response_structure(cfg):
    processed = {"term_lemmas": ["ключ"], "hints_lemmas": [["техника"]]}
    r = fallback_response("ключ", processed, cfg)
    for key in ("status", "term", "selected_context", "parameters", "warnings"):
        assert key in r
    assert all(p["confidence"] == 0.3 for p in r["parameters"])
    assert all(p["source"] == "template" for p in r["parameters"])
    assert len(r["warnings"]) > 0


def test_load_json_config_missing():
    result = load_json_config("/no/such/file.json")
    assert result == {}


def test_fallback_empty_lemmas(cfg):
    processed = {"term_lemmas": [], "hints_lemmas": []}
    r = fallback_response("ключ", processed, cfg)
    assert r["status"] == "ok"
    assert len(r["parameters"]) > 0
