import json
import pytest
from pathlib import Path
from src.config import Config
from src.lemmatizer import Lemmatizer
from src.synonyms import SynonymDict
from src.preprocess import preprocess_full

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


@pytest.fixture
def syn(tmp_path):
    data = {
        "ключ": [{"word": "инструмент", "weight": 0.8}],
        "техника": [{"word": "механизм", "weight": 0.7}],
    }
    p = tmp_path / "syn.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return SynonymDict(p)


def test_weights_simple(cfg, lm, syn):
    r = preprocess_full("ключ", ["техника"], cfg, syn, lm)
    assert r["status"] == "ok"
    tw = dict(r["tokens_with_weights"])
    assert tw["ключ"] == pytest.approx(0.7, abs=1e-5)
    assert tw["техника"] == pytest.approx(0.3, abs=1e-5)
    assert "инструмент" in tw
    assert "механизм" in tw
    # 2 синонима, каждый 0.1/2
    assert tw["инструмент"] == pytest.approx(0.05, abs=1e-5)


def test_weights_multi_word_term(cfg, lm, syn):
    r = preprocess_full("ключ гаечный", [], cfg, syn, lm)
    assert r["status"] == "ok"
    tw = dict(r["tokens_with_weights"])
    assert tw["ключ"] == pytest.approx(0.35, abs=1e-5)
    assert tw["гаечный"] == pytest.approx(0.35, abs=1e-5)
    # синоним только для 'ключ', 0.1/1 = 0.1
    assert tw["инструмент"] == pytest.approx(0.1, abs=1e-5)


def test_no_synonyms_flag(cfg, lm, syn):
    from dataclasses import replace

    cfg_no_syn = replace(cfg, use_synonyms=False)
    r = preprocess_full("ключ", ["техника"], cfg_no_syn, syn, lm)
    assert r["status"] == "ok"
    tokens = [t for t, _ in r["tokens_with_weights"]]
    assert "инструмент" not in tokens
    assert "механизм" not in tokens


def test_error_propagated(cfg, lm, syn):
    r = preprocess_full("!!!", [], cfg, syn, lm)
    assert r["status"] == "error"
