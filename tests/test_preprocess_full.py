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
        "\u043a\u043b\u044e\u0447": [{"word": "\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442", "weight": 0.8}],
        "\u0442\u0435\u0445\u043d\u0438\u043a\u0430": [{"word": "\u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c", "weight": 0.7}],
    }
    p = tmp_path / "syn.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return SynonymDict(p)


def test_weights_simple(cfg, lm, syn):
    r = preprocess_full("\u043a\u043b\u044e\u0447", ["\u0442\u0435\u0445\u043d\u0438\u043a\u0430"], cfg, syn, lm)
    assert r["status"] == "ok"
    tw = dict(r["tokens_with_weights"])
    assert tw["\u043a\u043b\u044e\u0447"] == pytest.approx(0.7, abs=1e-5)
    assert tw["\u0442\u0435\u0445\u043d\u0438\u043a\u0430"] == pytest.approx(0.3, abs=1e-5)
    assert "\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442" in tw
    assert "\u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c" in tw
    # 2 \u0441\u0438\u043d\u043e\u043d\u0438\u043c\u0430, \u043a\u0430\u0436\u0434\u044b\u0439 0.1/2
    assert tw["\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442"] == pytest.approx(0.05, abs=1e-5)

def test_weights_multi_word_term(cfg, lm, syn):
    r = preprocess_full("\u043a\u043b\u044e\u0447 \u0433\u0430\u0435\u0447\u043d\u044b\u0439", [], cfg, syn, lm)
    assert r["status"] == "ok"
    tw = dict(r["tokens_with_weights"])
    assert tw["\u043a\u043b\u044e\u0447"] == pytest.approx(0.35, abs=1e-5)
    assert tw["\u0433\u0430\u0435\u0447\u043d\u044b\u0439"] == pytest.approx(0.35, abs=1e-5)
    # \u0441\u0438\u043d\u043e\u043d\u0438\u043c \u0442\u043e\u043b\u044c\u043a\u043e \u0434\u043b\u044f '\u043a\u043b\u044e\u0447', 0.1/1 = 0.1
    assert tw["\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442"] == pytest.approx(0.1, abs=1e-5)

def test_no_synonyms_flag(cfg, lm, syn):
    from dataclasses import replace
    cfg_no_syn = replace(cfg, use_synonyms=False)
    r = preprocess_full("\u043a\u043b\u044e\u0447", ["\u0442\u0435\u0445\u043d\u0438\u043a\u0430"], cfg_no_syn, syn, lm)
    assert r["status"] == "ok"
    tokens = [t for t, _ in r["tokens_with_weights"]]
    assert "\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442" not in tokens
    assert "\u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c" not in tokens

def test_error_propagated(cfg, lm, syn):
    r = preprocess_full("!!!", [], cfg, syn, lm)
    assert r["status"] == "error"