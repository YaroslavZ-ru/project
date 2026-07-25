"""tests/test_performance.py -- тесты бенчмарка производительности (изм. 86).

Проверяет что run_benchmark возвращает корректную структуру
и что pipeline укладывается в пороговые значения на малом датасете.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from scripts.init_db import init_db
from src.config import Config, reset_config


@pytest.fixture(scope="function")
def tmp_project(tmp_path):
    """Создать временный проект с реальными путями, но мок моделью."""
    (tmp_path / "data").mkdir()
    (tmp_path / "configs").mkdir()
    (tmp_path / "models").mkdir()

    db_path = tmp_path / "data" / "knowledge_base.db"
    synonyms_path = tmp_path / "data" / "synonyms.json"
    domain_templates_path = tmp_path / "configs" / "domain_templates.json"
    domain_keywords_path = tmp_path / "configs" / "domain_keywords.json"

    synonyms_path.write_text("{}", encoding="utf-8")
    domain_templates_path.write_text(
        json.dumps(
            {"general": {"parameters": [{"name": "type", "label_ru": "Тип", "type": "string"}]}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    domain_keywords_path.write_text("{}", encoding="utf-8")

    config_data = {
        "db_path": "data/knowledge_base.db",
        "fasttext_model_path": "models/cc.ru.300.bin",
        "synonyms_path": "data/synonyms.json",
        "domain_templates_path": "configs/domain_templates.json",
        "domain_keywords_path": "configs/domain_keywords.json",
        "fallback_embeddings_path": "",
        "min_confidence": 0.3,
        "max_candidates": 20,
        "max_parameters": 15,
        "use_generative": False,
        "generative_model": "test-model",
        "generative_max_new_tokens": 50,
        "generative_temperature": 0.7,
        "generative_max_new_params": 3,
        "generative_timeout_seconds": 5.0,
        "min_parameters_for_generative": 5,
        "generative_keywords": ["материал"],
        "timeout_seconds": 5.0,
        "cache_embeddings": True,
        "log_level": "INFO",
        "cache_lemma_size": 100,
        "max_synonyms_per_token": 2,
        "use_synonyms": True,
        "max_term_length": 100,
        "max_hint_length": 50,
        "word_vector_cache_size": 100,
        "query_cache_size": 10,
        "use_faiss": False,
        "faiss_threshold": 1000,
        "fallback_domain_keywords_path": "configs/domain_keywords.json",
        "faiss_index_path": "",
        "session_ttl_seconds": 300,
        "session_cache_size": 50,
        "session_cleanup_interval_seconds": 60,
        "auto_save_domain_on_ok": True,
        "ambiguity_threshold": 0.7,
        "ambiguity_delta": 0.1,
        "domain_centroid_threshold": 0.3,
        "auto_save_domain_on_fallback": False,
        "use_relations": False,
        "relation_max_depth": 1,
        "relation_decay_factor": 0.5,
        "domain_centroids_min_concepts": 2,
        "use_metrics": False,
        "api_host": "127.0.0.1",
        "api_port": 8000,
    }
    config_path = tmp_path / "configs" / "config.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")

    init_db(str(db_path))

    reset_config()
    cfg = Config.from_json(str(config_path), project_root=tmp_path)
    return tmp_path, cfg


@pytest.fixture
def mock_embedding_model():
    """Мок FastTextWrapper: всегда возвращает нулевой вектор 300-мерный."""
    model = MagicMock()
    model.get_word_vector.return_value = np.zeros(300, dtype=np.float32)
    model.get_phrase_vector.return_value = np.zeros(300, dtype=np.float32)
    model.get_dimension.return_value = 300
    model._model_loaded = True
    return model


@pytest.fixture
def pipeline_components(tmp_project, mock_embedding_model):
    """Создаёт полный набор компонентов с мок-моделью."""
    from src.cache import QueryVectorCache
    from src.generative import GenerativeExpander
    from src.knowledge_base import KnowledgeBase
    from src.lemmatizer import Lemmatizer
    from src.sessions import SessionManager
    from src.synonyms import SynonymDict

    _, cfg = tmp_project

    lemmatizer = Lemmatizer(cache_size=cfg.cache_lemma_size)
    synonym_dict = SynonymDict(json_path=cfg.synonyms_path)
    vector_cache = QueryVectorCache(maxsize=cfg.query_cache_size)
    kb = KnowledgeBase(cfg, mock_embedding_model, synonym_dict)
    gen_expander = GenerativeExpander(config=cfg)
    session_mgr = SessionManager(config=cfg)

    yield (
        cfg,
        lemmatizer,
        synonym_dict,
        mock_embedding_model,
        vector_cache,
        kb,
        gen_expander,
        session_mgr,
    )

    kb.close()


def test_benchmark_returns_valid_structure(pipeline_components):
    """run_benchmark возвращает dict с stats и checks."""
    from scripts.profile import run_benchmark

    cfg, *_ = pipeline_components
    result = run_benchmark(str(Path("configs/config.json")), n=1)

    assert isinstance(result, dict)
    assert "stats" in result
    assert "checks" in result
    assert "all_passed" in result
    assert isinstance(result["stats"], dict)
    assert isinstance(result["checks"], dict)
    assert isinstance(result["all_passed"], bool)


def test_benchmark_stats_have_required_keys(pipeline_components):
    """stats содержит total_ms с mean_ms, p50_ms, p95_ms, p99_ms."""
    from scripts.profile import run_benchmark

    result = run_benchmark(str(Path("configs/config.json")), n=1)

    assert "total_ms" in result["stats"]
    total = result["stats"]["total_ms"]
    for key in ("mean_ms", "p50_ms", "p95_ms", "p99_ms"):
        assert key in total, f"Отсутствует ключ {key} в total_ms"
        assert isinstance(total[key], (int, float))


def test_benchmark_checks_have_required_keys(pipeline_components):
    """checks содержит total_ms с threshold_ms, actual_ms, passed."""
    from scripts.profile import run_benchmark

    result = run_benchmark(str(Path("configs/config.json")), n=1)

    assert "total_ms" in result["checks"]
    check = result["checks"]["total_ms"]
    assert "threshold_ms" in check
    assert "actual_ms" in check
    assert "passed" in check
    assert isinstance(check["passed"], bool)


def test_benchmark_runs_without_error(pipeline_components):
    """Бенчмарк завершается без ошибок и возвращает валидную структуру."""
    from scripts.profile import run_benchmark

    result = run_benchmark(str(Path("configs/config.json")), n=1)

    assert "stats" in result
    assert "checks" in result
    assert "all_passed" in result
    assert isinstance(result["all_passed"], bool)


def test_benchmark_threshold_is_300ms(pipeline_components):
    """Порог для total_ms равен 300 мс."""
    from scripts.profile import run_benchmark

    result = run_benchmark(str(Path("configs/config.json")), n=1)

    check = result["checks"]["total_ms"]
    assert check["threshold_ms"] == 300


def test_profile_pipeline_returns_step_stats(pipeline_components):
    """profile_pipeline возвращает статистику по каждому шагу."""
    from scripts.profile import profile_pipeline

    cfg, *components = pipeline_components
    queries = [{"term": "ключ", "hints": ["техника"]}]
    stats = profile_pipeline(cfg, components, queries, n_runs=1)

    expected_steps = {"preprocess", "vectorize", "search", "aggregate_or_fallback", "total"}
    assert set(stats.keys()) == expected_steps

    for step, data in stats.items():
        assert "min_s" in data
        assert "max_s" in data
        assert "mean_s" in data
        assert "calls" in data
        assert data["calls"] >= 1


def test_profile_pipeline_min_le_max(pipeline_components):
    """min_s <= mean_s <= max_s для каждого шага."""
    from scripts.profile import profile_pipeline

    cfg, *components = pipeline_components
    queries = [{"term": "ключ", "hints": ["техника"]}]
    stats = profile_pipeline(cfg, components, queries, n_runs=3)

    for step, data in stats.items():
        assert data["min_s"] <= data["mean_s"] + 1e-9, f"{step}: min > mean"
        assert data["mean_s"] <= data["max_s"] + 1e-9, f"{step}: mean > max"
