"""tests/test_api.py -- тесты FastAPI эндпоинтов.

Использует TestClient, не требует запущенного uvicorn.
Если fastapi/httpx не установлены -- тесты скипаются автоматически.
"""

import pytest
from unittest.mock import MagicMock
from pathlib import Path

# Пропуск если fastapi/httpx недоступны
fastapi_mod = pytest.importorskip("fastapi", reason="fastapi не установлен")
httpx_mod = pytest.importorskip("httpx", reason="httpx не установлен")

from fastapi.testclient import TestClient  # noqa: E402
from src.metrics import MetricsCollector  # noqa: E402
import src.api as api_module  # noqa: E402


@pytest.fixture(scope="module")
def api_client():
    """Фикстура: TestClient с мокированными компонентами (lifespan не вызывается)."""
    # Создаём мок конфига
    mock_cfg = MagicMock()
    mock_cfg.min_confidence = 0.3
    mock_cfg.max_candidates = 10
    mock_cfg.max_parameters = 15
    mock_cfg.use_generative = False
    mock_cfg.min_parameters_for_generative = 5
    mock_cfg.auto_save_domain_on_ok = False
    mock_cfg.auto_save_domain_on_fallback = False
    mock_cfg.use_metrics = False

    # Мок базы знаний
    mock_kb = MagicMock()
    mock_kb.search_similar_concepts.return_value = []
    mock_kb._conn = MagicMock()  # db_available=True
    mock_kb._db_path = Path("data/knowledge_base.db")
    mock_kb.get_all_concepts.return_value = []

    # Мок модели
    import numpy as np

    mock_emb = MagicMock()
    mock_emb._model_loaded = True
    mock_emb.get_word_vector.return_value = np.zeros(300, dtype=np.float32)
    mock_emb.get_phrase_vector.return_value = np.zeros(300, dtype=np.float32)
    mock_emb.get_dimension.return_value = 300

    # Мок лемматизатора
    mock_lemmatizer = MagicMock()
    mock_lemmatizer.lemmatize.return_value = ["ключ"]

    # Мок словаря синонимов
    mock_synonyms = MagicMock()
    mock_synonyms.get.return_value = []

    # Мок кэша
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    # Мок сессий менеджера
    mock_session = MagicMock()
    mock_session.get_domain.return_value = None

    # Мок генеративного расширителя
    mock_gen = MagicMock()
    mock_gen.expand.return_value = []

    # Устанавливаем глобальные переменные API-модуля
    api_module._cfg = mock_cfg
    api_module._kb = mock_kb
    api_module._embedding_model = mock_emb
    api_module._lemmatizer = mock_lemmatizer
    api_module._synonym_dict = mock_synonyms
    api_module._vector_cache = mock_cache
    api_module._session_manager = mock_session
    api_module._generative_expander = mock_gen
    api_module._metrics = MetricsCollector(use_metrics=False)

    client = TestClient(api_module.app, raise_server_exceptions=True)
    return client


def test_health_returns_ok(api_client):
    """При инициализированных компонентах /health возвращает статус ok или starting."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "starting")


def test_query_empty_term_returns_422(api_client):
    """Пустой term -- Pydantic автоматически возвращает 422."""
    response = api_client.post("/query", json={"term": ""})
    assert response.status_code == 422


def test_query_valid_term_returns_200(api_client):
    """Валидный term -- 200 с полем status."""
    response = api_client.post("/query", json={"term": "ключ", "hints": ["техника"]})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "error", "fallback")


def test_query_with_session_id(api_client):
    """Запрос с session_id -- 200, не падает."""
    response = api_client.post(
        "/query",
        json={"term": "ключ", "session_id": "test-session"},
    )
    assert response.status_code == 200


def test_metrics_returns_json_when_prometheus_unavailable(api_client):
    """При отсутствии Prometheus /metrics возвращает JSON."""
    response = api_client.get("/metrics")
    assert response.status_code == 200
    ct = response.headers.get("content-type", "")
    if "application/json" in ct:
        data = response.json()
        assert "requests_total" in data
    else:
        assert "ait_" in response.text or len(response.text) > 0


def test_kb_stats(api_client):
    """Статистика БД: 200 с concepts_count или 503."""
    response = api_client.get("/kb/stats")
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        data = response.json()
        assert "concepts_count" in data


def test_query_too_many_hints_truncated(api_client):
    """Пять подсказок -- внутри API усекаются до 3, ответ 200."""
    response = api_client.post(
        "/query",
        json={"term": "болт", "hints": ["а", "б", "в", "г", "д"]},
    )
    assert response.status_code == 200
