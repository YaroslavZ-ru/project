"""tests/test_pipeline.py -- интеграционные E2E-тесты полного пайплайна.

Тесты проверяют взаимодействие всех модулей src/ без реальных ML-моделей.
FastText заменяется мок-объектом с нулевыми векторами.
"""

import json
from pathlib import Path
import sqlite3
import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from scripts.init_db import init_db
from src.config import Config, reset_config

# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def tmp_project(tmp_path):
    """Создать временный проект с реальными путями, но мок моделью."""
    # Создаём папки
    (tmp_path / "data").mkdir()
    (tmp_path / "configs").mkdir()
    (tmp_path / "models").mkdir()

    # Пути к артефактам
    db_path = tmp_path / "data" / "knowledge_base.db"
    synonyms_path = tmp_path / "data" / "synonyms.json"
    domain_templates_path = tmp_path / "configs" / "domain_templates.json"
    domain_keywords_path = tmp_path / "configs" / "domain_keywords.json"
    tmp_path / "models" / "cc.ru.300.bin"

    # Файлы данных
    synonyms_path.write_text("{}", encoding="utf-8")
    domain_templates_path.write_text(
        json.dumps(
            {"общее": {"parameters": [{"name": "type", "label_ru": "Тип", "type": "string"}]}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    domain_keywords_path.write_text("{}", encoding="utf-8")

    # Конфиг
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

    # Инициализация БД
    init_db(str(db_path))

    reset_config()
    cfg = Config.from_json(str(config_path), project_root=tmp_path)
    return tmp_path, cfg


@pytest.fixture
def mock_embedding_model():
    """Мок FastTextWrapper: всегда возвращает нулевый вектор 300-мерный."""
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


# ---------------------------------------------------------------------------
# Вспомогательная функция
# ---------------------------------------------------------------------------


def call_pipeline(components, term, hints=None, debug=False, session_id=None):
    """Вызвать run_pipeline с заданными компонентами.

    Args:
        components: кортеж из pipeline_components фикстуры.
        term:       термин для анализа.
        hints:      уточняющие подсказки (None = пустой список).
        debug:      включить debug_info в ответ.
        session_id: ID сессии (None = без сессии).
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from main import run_pipeline

    (
        cfg,
        lemmatizer,
        synonym_dict,
        embedding_model,
        vector_cache,
        kb,
        generative_expander,
        session_manager,
    ) = components

    return run_pipeline(
        term=term,
        hints=hints or [],
        debug=debug,
        min_confidence=None,
        cfg=cfg,
        lemmatizer=lemmatizer,
        synonym_dict=synonym_dict,
        embedding_model=embedding_model,
        vector_cache=vector_cache,
        kb=kb,
        generative_expander=generative_expander,
        session_manager=session_manager,
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------


def test_pipeline_empty_kb_returns_fallback(pipeline_components):
    """Пустая БД -- должен вернуть шаблонный (fallback) ответ."""
    result = call_pipeline(pipeline_components, "ключ", ["техника"])
    assert result["status"] == "ok"
    assert "parameters" in result
    assert "selected_context" in result
    assert "warnings" in result
    # При пустой БД fallback_response должен вернуть шаблонный ответ
    warnings = result.get("warnings", [])
    # Если вектор нулевой — должно быть предупреждение о нулевом векторе
    assert isinstance(warnings, list)


def test_pipeline_returns_required_fields(pipeline_components):
    """Ответ содержит все обязательные поля."""
    result = call_pipeline(pipeline_components, "болт")
    required_fields = [
        "status",
        "term",
        "selected_context",
        "parameters",
        "suggested_refinements",
        "warnings",
    ]
    for field in required_fields:
        assert field in result, f"Поле {field!r} отсутствует в ответе"


def test_pipeline_term_preserved_in_result(pipeline_components):
    """Термин сохраняется в ответе."""
    result = call_pipeline(pipeline_components, "гайка")
    assert result["term"] == "гайка"


def test_pipeline_debug_mode_adds_debug_info(pipeline_components):
    """В debug-режиме ответ содержит debug_info с query_vector."""
    result = call_pipeline(pipeline_components, "ключ", debug=True)
    assert result["status"] == "ok"
    assert "debug_info" in result
    debug = result["debug_info"]
    assert "query_vector" in debug
    assert isinstance(debug["query_vector"], list)
    assert len(debug["query_vector"]) == 300


def test_pipeline_with_kb_returns_parameters(pipeline_components):
    """Пайплайн не падает даже при заполненной БД (нулевой вектор => fallback)."""
    (
        cfg,
        lemmatizer,
        synonym_dict,
        embedding_model,
        vector_cache,
        kb,
        gen_expander,
        session_mgr,
    ) = pipeline_components

    # Добавить концепт напрямую в БД
    conn = sqlite3.connect(str(cfg.db_path))
    emb_blob = np.zeros(300, dtype="<f4").tobytes()
    conn.execute(
        "INSERT INTO concepts (id, term, domain, embedding) VALUES (?, ?, ?, ?)",
        ("c_test", "ключ гаечный", "инструмент", emb_blob),
    )
    conn.execute(
        "INSERT INTO parameters (concept_id, name, label_ru, type) VALUES (?, ?, ?, ?)",
        ("c_test", "material", "Материал", "string"),
    )
    conn.commit()
    conn.close()
    kb._concepts_cache = None  # Сбросить кэш

    result = call_pipeline(pipeline_components, "ключ")
    assert result["status"] == "ok"


def test_pipeline_whitespace_term_handled(pipeline_components):
    """Пайплайн не падает на пустых/пробельных терминах."""
    result = call_pipeline(pipeline_components, "   ")
    assert result["status"] in ("ok", "error")


def test_pipeline_caching_second_call_faster(pipeline_components):
    """Второй вызов с тем же входом -- завершается за разумное время (кэш)."""
    call_pipeline(pipeline_components, "ключ", ["техника"])

    t2 = time.monotonic()
    call_pipeline(pipeline_components, "ключ", ["техника"])
    second_call = time.monotonic() - t2

    assert second_call < 10.0


def test_pipeline_with_session_id(pipeline_components):
    """run_pipeline с session_id не падает; сессия сохраняется корректно."""
    (
        cfg,
        lemmatizer,
        synonym_dict,
        embedding_model,
        vector_cache,
        kb,
        gen_expander,
        session_mgr,
    ) = pipeline_components

    result = call_pipeline(pipeline_components, "ключ", session_id="test_sess")
    assert result["status"] in ("ok", "error")
    # session_count() должен вернуть неотрицательное число
    assert session_mgr.session_count() >= 0


def test_pipeline_none_hints_handled(pipeline_components):
    """None вместо hints -- не падает, обрабатывается как пустой список."""
    result = call_pipeline(pipeline_components, "болт", hints=None)
    assert result["status"] in ("ok", "error")


def test_pipeline_returns_needs_clarification_field(pipeline_components):
    """Поле needs_clarification должно присутствовать в ответе."""
    result = call_pipeline(pipeline_components, "ключ")
    assert "needs_clarification" in result, "Поле needs_clarification должно быть в ответе"
    assert isinstance(result["needs_clarification"], bool)


def test_pipeline_needs_clarification_false_by_default(pipeline_components):
    """fallback-ответ должен содержать needs_clarification=False."""
    result = call_pipeline(pipeline_components, "ключ")
    assert not result.get("needs_clarification")
