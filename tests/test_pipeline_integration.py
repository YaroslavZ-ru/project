import numpy as np
import pytest
from pathlib import Path
from src.config import Config
from src.lemmatizer import Lemmatizer
from src.synonyms import SynonymDict
from src.cache import QueryVectorCache
from main import run_pipeline

PROJECT_ROOT = Path(__file__).parent.parent


class MockEmbedding:
    def get_phrase_vector(self, phrase):
        v = np.zeros(300, dtype=np.float32)
        v[0] = 1.0
        return v

    def get_dimension(self):
        return 300


@pytest.fixture(autouse=True)
def reset_lemmatizer():
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
def syn():
    return SynonymDict(PROJECT_ROOT / "data" / "synonyms.json")


@pytest.fixture
def emb():
    return MockEmbedding()


@pytest.fixture
def vcache():
    return QueryVectorCache(maxsize=10)


def test_basic_ok(cfg, lm, syn, emb, vcache):
    r = run_pipeline("ключ", ["техника"], False, None, cfg, lm, syn, emb, vcache)
    assert r["status"] == "ok"
    for f in (
        "term",
        "selected_context",
        "parameters",
        "suggested_refinements",
        "warnings",
    ):
        assert f in r
    assert "debug_info" not in r


def test_debug_info(cfg, lm, syn, emb, vcache):
    r = run_pipeline("ключ", [], True, None, cfg, lm, syn, emb, vcache)
    assert "debug_info" in r
    assert set(r["debug_info"].keys()) == {
        "query_vector",
        "candidates_raw",
        "scores_distribution",
    }
    assert len(r["debug_info"]["query_vector"]) == 300


def test_cache_hit(cfg, lm, syn, emb, vcache):
    count = [0]
    orig = emb.get_phrase_vector

    def counting(p):
        count[0] += 1
        return orig(p)

    emb.get_phrase_vector = counting
    run_pipeline("ключ", ["техника"], False, None, cfg, lm, syn, emb, vcache)
    first = count[0]
    run_pipeline("ключ", ["техника"], False, None, cfg, lm, syn, emb, vcache)
    assert count[0] == first


def test_empty_term_error(cfg, lm, syn, emb, vcache):
    assert (
        run_pipeline("!!!", [], False, None, cfg, lm, syn, emb, vcache)["status"]
        == "error"
    )


def test_none_hints_ok(cfg, lm, syn, emb, vcache):
    assert (
        run_pipeline("ключ", None, False, None, cfg, lm, syn, emb, vcache)["status"]
        == "ok"
    )
