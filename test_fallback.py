from pathlib import Path

import pytest

from src.config import Config
from src.fallback import detect_domain, fallback_response, load_json_config
from src.lemmatizer import Lemmatizer

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
    result = detect_domain(all_lemmas, str(PROJECT_ROOT / "configs" / "domain_keywords.json"))
    assert result == "музыка"


def test_detect_domain_no_match():
    result = detect_domain({"хмурыкало"}, str(PROJECT_ROOT / "configs" / "domain_keywords.json"))
    assert result == "general"


def test_fallback_response_structure(cfg):
    processed = {"term_lemmas": ["ключ"], "hints_lemmas": [["техника"]]}
    r = fallback_response("ключ", processed, cfg)
    for key in ("status", "term", "selected_context", "parameters", "warnings"):
        assert key in r
    assert all(p["confidence"] == 0.4 for p in r["parameters"])
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


# --- Изменение 76: Тесты confidence=0.4 и домен "general" ---


def test_fallback_confidence_is_0_4(cfg):
    """fallback_response возвращает parameters с confidence=0.4."""
    processed = {"term_lemmas": ["абракадабра"], "hints_lemmas": []}
    r = fallback_response("абракадабра", processed, cfg)
    for p in r["parameters"]:
        assert p["confidence"] == 0.4


def test_detect_domain_returns_general_when_no_match():
    """all_lemmas не содержит ни одного ключевого слова -> general."""
    keywords_path = str(PROJECT_ROOT / "configs" / "domain_keywords.json")
    domain = detect_domain({"абракадабра"}, keywords_path)
    assert domain == "general"


def test_detect_domain_general_not_in_competition():
    """general не должен побеждать если есть совпадения в другом домене."""
    keywords_path = str(PROJECT_ROOT / "configs" / "domain_keywords.json")
    domain = detect_domain({"ключ", "инструмент"}, keywords_path)
    assert domain != "general"
