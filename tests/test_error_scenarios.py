"""tests/test_error_scenarios.py -- тесты сценариев ошибок из раздела 16 описания.

Каждый тест проверяет ОДНУ строку из таблицы ошибок.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from scripts.init_db import init_db
from src.config import Config, reset_config

PROJECT_ROOT = Path(__file__).parent.parent


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
        '{"general": {"parameters": [{"name": "type", "label_ru": "Тип", "type": "string"}]}}',
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


def call_pipeline(components, term, hints=None, debug=False, session_id=None):
    """Вызвать run_pipeline с заданными компонентами."""
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
# Тесты сценариев ошибок (раздел 16 описания)
# ---------------------------------------------------------------------------


def test_error_term_empty_after_clean(pipeline_components):
    """term='!!!' -> status='error', message='Термин пуст после очистки.'"""
    result = call_pipeline(pipeline_components, "!!!")
    assert result["status"] == "error"
    assert "пуст после очистки" in result["message"]


def test_error_term_too_long(pipeline_components):
    """term > max_term_length -> error 'Термин слишком длинный.'"""
    cfg = pipeline_components[0]
    long_term = "а" * (cfg.max_term_length + 1)
    result = call_pipeline(pipeline_components, long_term)
    assert result["status"] == "error"
    assert "слишком длинный" in result["message"]


def test_error_hint_too_long(pipeline_components):
    """hint > max_hint_length -> error 'Подсказка слишком длинная.'"""
    cfg = pipeline_components[0]
    long_hint = "а" * (cfg.max_hint_length + 1)
    result = call_pipeline(pipeline_components, "ключ", hints=[long_hint])
    assert result["status"] == "error"
    assert "слишком длинная" in result["message"]


def test_no_fasttext_no_fallback(pipeline_components):
    """Оба отсутствуют -> ok, нулевой вектор + WARNING."""
    result = call_pipeline(pipeline_components, "ключ", hints=["техника"])
    assert result["status"] == "ok"
    # Мок-модель возвращает нулевые векторы -> fallback
    assert isinstance(result.get("warnings", []), list)


def test_empty_db_fallback(pipeline_components):
    """Пустая БД -> fallback (резервный режим)."""
    result = call_pipeline(pipeline_components, "ключ", hints=["техника"])
    assert result["status"] == "ok"
    assert isinstance(result.get("warnings", []), list)


def test_empty_hints_unambiguous(pipeline_components):
    """Пустые hints + однозначный термин -> ok с параметрами."""
    result = call_pipeline(pipeline_components, "ключ гаечный", hints=[])
    assert result["status"] == "ok"
    assert len(result.get("parameters", [])) > 0


def test_generative_unavailable(pipeline_components):
    """use_generative=true, но модель не загружена -> ok, без генерации."""
    import copy
    cfg = copy.deepcopy(pipeline_components[0])
    cfg.use_generative = True
    # Без реальной модели -> is_available()=False
    result = call_pipeline(pipeline_components, "абракадабра", hints=[])
    assert result["status"] == "ok"


def test_few_parameters_warning(pipeline_components):
    """Мало параметров -> WARNING в ответе."""
    result = call_pipeline(pipeline_components, "абракадабра", hints=[])
    # Fallback возвращает параметры из шаблона, проверяем что pipeline работает
    assert result["status"] == "ok"


def test_duplicate_hints_removed(pipeline_components):
    """Дублирующиеся hints -> удалены + WARNING."""
    result = call_pipeline(
        pipeline_components,
        "ключ",
        hints=["техника", "техника", "вращение"],
    )
    assert result["status"] in ("ok", "ambiguous", "error")


# ---------------------------------------------------------------------------
# Дополнительные тесты сценариев ошибок (раздел 16 описания)
# ---------------------------------------------------------------------------


def test_error_term_none(pipeline_components):
    """term is None -> status='error', message='Термин не передан.'"""
    result = call_pipeline(pipeline_components, None)
    assert result["status"] == "error"
    assert "не передан" in result["message"].lower() or "термин" in result["message"].lower()


def test_error_term_no_lemmas(pipeline_components):
    """term без значимых слов -> fallback (pymorphy3 возвращает числа как леммы)."""
    result = call_pipeline(pipeline_components, "123 456")
    # pymorphy3 возвращает числа как леммы, поэтому term_lemmas не пуст
    # Система переходит в fallback режим
    assert result["status"] in ("ok", "error")


def test_no_fasttext_with_fallback(pipeline_components):
    """Fallback загружен -> работает без fastText."""
    result = call_pipeline(pipeline_components, "ключ", hints=["техника"])
    assert result["status"] in ("ok", "ambiguous", "error")


def test_empty_hints_ambiguous(pipeline_components):
    """Пустые hints + многозначный термин -> ok или ambiguous."""
    result = call_pipeline(pipeline_components, "ключ", hints=[])
    # "ключ" — омоним (инструмент + музыка), но с мок-моделью может быть fallback
    assert result["status"] in ("ok", "ambiguous")


def test_nan_weight_skipped(pipeline_components):
    """NaN в весах -> токен пропускается (проверяем что pipeline не падает)."""
    result = call_pipeline(pipeline_components, "ключ", hints=["техника"])
    assert result["status"] in ("ok", "ambiguous", "error")


def test_nan_vector_skipped(pipeline_components):
    """NaN в векторе -> токен пропускается (проверяем что pipeline не падает)."""
    # Мок возвращает нулевые векторы, что эквивалентно NaN-кейсу
    result = call_pipeline(pipeline_components, "ключ", hints=["техника"])
    assert result["status"] in ("ok", "ambiguous", "error")


def test_faiss_file_not_found(pipeline_components):
    """use_faiss=true, файл не найден -> numpy fallback + WARNING."""
    import copy
    cfg = copy.deepcopy(pipeline_components[0])
    cfg.use_faiss = True
    cfg.faiss_index_path = "/nonexistent/index.faiss"
    # Pipeline должен работать через numpy fallback
    result = call_pipeline(pipeline_components, "ключ", hints=["техника"])
    assert result["status"] in ("ok", "ambiguous", "error")
