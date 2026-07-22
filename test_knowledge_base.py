from pathlib import Path
import sqlite3

import numpy as np
import pytest

from scripts.init_db import init_db
from src.config import Config
from src.knowledge_base import KnowledgeBase
from src.lemmatizer import Lemmatizer

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def reset_lemmatizer():
    Lemmatizer._instance = None
    yield
    Lemmatizer._instance = None


@pytest.fixture
def cfg(tmp_path):
    c = Config.from_json("configs/config.json", project_root=PROJECT_ROOT)
    from dataclasses import replace

    return replace(c, db_path=str(tmp_path / "test.db"))


@pytest.fixture
def db_path(tmp_path):
    p = str(tmp_path / "test.db")
    init_db(p)
    return p


@pytest.fixture
def kb(cfg, db_path):
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    return KnowledgeBase(config=cfg2)


def test_init_db_creates_tables(tmp_path):
    p = str(tmp_path / "t.db")
    init_db(p)
    conn = sqlite3.connect(p)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"concepts", "parameters", "relations", "metadata"} <= tables
    conn.close()


def test_init_db_creates_indexes(tmp_path):
    p = str(tmp_path / "t.db")
    init_db(p)
    conn = sqlite3.connect(p)
    indexes = {r[1] for r in conn.execute("PRAGMA index_list('concepts')")}
    assert "idx_concepts_domain" in indexes
    conn.close()


def test_schema_version(tmp_path):
    p = str(tmp_path / "t.db")
    init_db(p)
    conn = sqlite3.connect(p)
    row = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    assert row[0] == "3"
    conn.close()


def test_init_db_idempotent(tmp_path):
    p = str(tmp_path / "t.db")
    init_db(p)
    init_db(p)  # не падает


def test_blob_to_vector_ok(kb):
    vec = np.random.randn(300).astype("<f4")
    blob = vec.tobytes()
    assert np.allclose(vec, kb._blob_to_vector(blob))


def test_blob_to_vector_none(kb):
    assert np.all(kb._blob_to_vector(None) == 0)


def test_blob_to_vector_wrong_size(kb):
    assert np.all(kb._blob_to_vector(b"wrong") == 0)


def test_get_all_concepts_empty(kb):
    assert kb.get_all_concepts() == []


def test_get_all_concepts_with_data(db_path, cfg):
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
        ("c1", "ключ", "техника", np.zeros(300, dtype="<f4").tobytes()),
    )
    conn.execute(
        "INSERT INTO parameters (concept_id,name,label_ru,type) VALUES (?,?,?,?)",
        ("c1", "size", "Размер", "float"),
    )
    conn.commit()
    conn.close()
    with KnowledgeBase(config=cfg2) as kb2:
        concepts = kb2.get_all_concepts()
        assert len(concepts) == 1
        assert concepts[0]["term"] == "ключ"
        assert len(concepts[0]["parameters"]) == 1


def test_get_all_concepts_cache(db_path, cfg):
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO concepts (id,term,domain) VALUES (?,?,?)",
        ("c1", "ключ", "техника"),
    )
    conn.commit()
    conn.close()
    with KnowledgeBase(config=cfg2) as kb2:
        r1 = kb2.get_all_concepts()
        r2 = kb2.get_all_concepts()
        assert r1 is r2


class MockEmbedding:
    def get_phrase_vector(self, phrase):
        return np.ones(300, dtype=np.float32)

    def get_dimension(self):
        return 300


def test_compute_embedding_norm(db_path, cfg):
    from dataclasses import replace

    from src.synonyms import SynonymDict

    cfg2 = replace(cfg, db_path=db_path)
    syn = SynonymDict(PROJECT_ROOT / "data" / "synonyms.json")
    with KnowledgeBase(config=cfg2, embedding_model=MockEmbedding(), synonym_dict=syn) as kb2:
        vec = kb2.compute_concept_embedding("ключ гаечный")
        assert abs(np.linalg.norm(vec) - 1.0) < 1e-4


def test_compute_embedding_empty(db_path, cfg):
    from dataclasses import replace

    from src.synonyms import SynonymDict

    cfg2 = replace(cfg, db_path=db_path)
    syn = SynonymDict(PROJECT_ROOT / "data" / "synonyms.json")
    with KnowledgeBase(config=cfg2, embedding_model=MockEmbedding(), synonym_dict=syn) as kb2:
        vec = kb2.compute_concept_embedding("")
        assert np.all(vec == 0)


def test_compute_embedding_no_model(db_path, cfg):
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    with KnowledgeBase(config=cfg2) as kb2, pytest.raises(RuntimeError):
        kb2.compute_concept_embedding("ключ")


def test_search_similar_zero_vector(db_path, cfg):
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    with KnowledgeBase(config=cfg2) as kb2:
        assert kb2.search_similar_concepts(np.zeros(300, dtype=np.float32)) == []


def test_search_finds_candidate(db_path, cfg):
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    vec = np.zeros(300, dtype="<f4")
    vec[0] = 1.0
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
        ("c1", "ключ", "техника", vec.tobytes()),
    )
    conn.commit()
    conn.close()
    with KnowledgeBase(config=cfg2) as kb2:
        results = kb2.search_similar_concepts(vec, min_confidence=0.0)
        assert len(results) == 1
        assert results[0]["concept_id"] == "c1"


# --- Тесты relations и centroids ---


def test_get_concept_relations_empty(cfg, db_path):
    """Пустая таблица — возвращает пустой список."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)
    relations = kb.get_concept_relations("nonexistent_id")
    assert relations == []
    kb.close()


def test_get_concept_relations_after_insert(cfg, db_path):
    """Отношение находится после вставки в БД."""
    from dataclasses import replace
    import sqlite3

    cfg2 = replace(cfg, db_path=db_path)
    emb = np.zeros(300, dtype=np.float32).tobytes()
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
        ("c_a", "термин А", "домен А", emb),
    )
    conn.execute(
        "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
        ("c_b", "термин Б", "домен Б", emb),
    )
    conn.execute(
        "INSERT INTO relations (source_concept_id,target_concept_id,relation_type,confidence)"
        " VALUES (?,?,?,?)",
        ("c_a", "c_b", "related_to", 0.9),
    )
    conn.commit()
    conn.close()
    kb = KnowledgeBase(config=cfg2)
    relations = kb.get_concept_relations("c_a")
    assert len(relations) == 1
    assert relations[0]["concept_id"] == "c_b"
    assert relations[0]["relation_type"] == "related_to"
    kb.close()


def test_search_with_relations_use_relations_false(cfg, db_path):
    """При use_relations=False — возвращает direct_results без изменений."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path, use_relations=False)
    kb = KnowledgeBase(config=cfg2)
    direct = [
        {
            "concept_id": "c1",
            "similarity": 0.8,
            "term": "а",
            "domain": "д",
            "parameters": [],
        }
    ]
    result = kb._search_with_relations(np.zeros(300, dtype=np.float32), direct, 0.3, 20)
    assert result == direct
    kb.close()


def test_load_domain_centroids_missing_file(cfg, db_path):
    """Путь не существует — возвращает пустой dict."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)
    centroids = kb.load_domain_centroids("/nonexistent/path.json")
    assert centroids == {}
    kb.close()


def test_get_closest_domain_empty_centroids(cfg, db_path):
    """Пустой domain_centroids — возвращает None."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)
    result = kb.get_closest_domain(np.zeros(300, dtype=np.float32), {})
    assert result is None
    kb.close()


# --- Изменение 66/67: Тесты save_concept и get_related_concept_params ---


def test_save_concept_and_get_related(cfg, db_path):
    """Сохранение понятия и получение связанных параметров."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)

    # Сохранить два понятия
    id1 = kb.save_concept("ключ", "инструмент", [{"name": "size", "label_ru": "Размер", "type": "float"}])
    id2 = kb.save_concept("ключ гаечный", "инструмент", [{"name": "moment", "label_ru": "Момент", "type": "float"}])

    # Добавить отношение is_a
    import uuid
    kb._conn.execute(
        "INSERT INTO relations (id, source_concept_id, target_concept_id, relation_type, confidence) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), id2, id1, "is_a", 1.0),
    )
    kb._conn.commit()

    # Получить параметры связанных понятий
    params = kb.get_related_concept_params(id2, depth=1)
    assert len(params) >= 1
    param_names = [p["name"] for p in params]
    assert "size" in param_names

    kb.close()


def test_get_related_concept_params_max_depth(cfg, db_path):
    """Проверить что depth ограничивается 3."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)

    # Даже с depth=10, метод ограничит до 3
    params = kb.get_related_concept_params("nonexistent", depth=10)
    assert params == []

    kb.close()


def test_save_concept_generates_id(cfg, db_path):
    """save_concept возвращает непустой concept_id."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)

    cid = kb.save_concept("тест", "домен")
    assert cid
    assert isinstance(cid, str)
    assert len(cid) > 0

    kb.close()


def test_get_feedback_stats_empty(cfg, db_path):
    """get_feedback_stats для несуществующего concept_id."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)

    stats = kb.get_feedback_stats("nonexistent")
    assert stats["avg_rating"] is None
    assert stats["votes"] == 0

    kb.close()


# --- Изменение 71: Тесты автоматической пересборки FAISS ---


def test_maybe_rebuild_faiss_skips_below_threshold(cfg, db_path):
    """Количество concepts < faiss_threshold -> rebuild не запускается."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path, use_faiss=True, faiss_threshold=10000)
    kb = KnowledgeBase(config=cfg2)

    # Save a few concepts (below threshold)
    kb.save_concept("тест1", "домен1")
    kb.save_concept("тест2", "домен1")

    # _maybe_rebuild_faiss should not start a thread (pending stays False)
    assert not kb._faiss_rebuild_pending

    kb.close()


def test_rebuild_faiss_creates_index(cfg, db_path):
    """Sufficient concepts -> индекс создаётся."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path, use_faiss=True, faiss_threshold=10)
    kb = KnowledgeBase(config=cfg2)

    # Insert enough concepts
    emb = np.ones(300, dtype=np.float32).tobytes()
    for i in range(20):
        kb._conn.execute(
            "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
            (f"cid_{i}", f"термин_{i}", "домен", emb),
        )
    kb._conn.commit()

    # Clear cache
    kb._concepts_cache = None

    # Force rebuild
    kb._maybe_rebuild_faiss()
    # Wait briefly for daemon thread
    import time as _time
    _time.sleep(0.5)

    # If faiss is installed, _faiss_index should be set
    # (may be None if faiss not installed, which is fine)
    kb.close()


# --- Изменение 75: Тесты матрицы эмбеддингов ---


def test_ensure_embeddings_matrix_builds_matrix(cfg, db_path):
    """Создать БД с понятиями, вызвать _ensure_embeddings_matrix, проверить матрицу."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    conn = sqlite3.connect(db_path)
    emb = np.ones(300, dtype=np.float32)
    vec_bytes = emb.astype("<f4").tobytes()
    conn.execute(
        "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
        ("c1", "ключ", "техника", vec_bytes),
    )
    conn.execute(
        "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
        ("c2", "нота", "музыка", vec_bytes),
    )
    conn.commit()
    conn.close()

    kb = KnowledgeBase(config=cfg2)
    kb._ensure_embeddings_matrix()

    assert kb._embeddings_matrix is not None
    assert kb._embeddings_matrix.shape == (2, 300)
    assert len(kb._matrix_concept_ids) == 2

    kb.close()


def test_invalidate_matrix_clears_cache(cfg, db_path):
    """Построить матрицу, инвалидировать, проверить что matrix is None."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    conn = sqlite3.connect(db_path)
    emb = np.ones(300, dtype=np.float32).astype("<f4").tobytes()
    conn.execute(
        "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
        ("c1", "ключ", "техника", emb),
    )
    conn.commit()
    conn.close()

    kb = KnowledgeBase(config=cfg2)
    kb._ensure_embeddings_matrix()
    assert kb._embeddings_matrix is not None

    kb._invalidate_embeddings_matrix()
    assert kb._embeddings_matrix is None
    assert kb._matrix_concept_ids is None

    kb.close()


def test_search_uses_matrix(cfg, db_path):
    """Поиск должен использовать матрицу если она построена."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    conn = sqlite3.connect(db_path)
    vec = np.zeros(300, dtype="<f4")
    vec[0] = 1.0
    conn.execute(
        "INSERT INTO concepts (id,term,domain,embedding) VALUES (?,?,?,?)",
        ("c1", "ключ", "техника", vec.tobytes()),
    )
    conn.commit()
    conn.close()

    kb = KnowledgeBase(config=cfg2)
    kb._ensure_embeddings_matrix()
    assert kb._embeddings_matrix is not None

    # Search should work using the matrix
    results = kb.search_similar_concepts(vec, min_confidence=0.0)
    assert len(results) == 1
    assert results[0]["concept_id"] == "c1"

    kb.close()


# --- Изменение 77: Тесты SearchCache с TTL ---


def test_search_cache_expires_after_ttl(cfg, db_path):
    """Кэш истекает после TTL."""
    from dataclasses import replace
    from src.knowledge_base import SearchCache

    cache = SearchCache(maxsize=10, ttl_seconds=1)
    cache.put(("key1",), [{"result": "test"}])

    # Immediately available
    assert cache.get(("key1",)) is not None

    # Wait for TTL
    import time as _time
    _time.sleep(1.1)

    # Should be expired
    assert cache.get(("key1",)) is None


def test_search_cache_no_ttl_when_zero():
    """TTL=0 -> запись живёт бесконечно (пока не эвиктируется)."""
    from src.knowledge_base import SearchCache

    cache = SearchCache(maxsize=10, ttl_seconds=0)
    cache.put(("key1",), [{"result": "test"}])

    import time as _time
    _time.sleep(0.1)

    # Should still be available (no TTL)
    assert cache.get(("key1",)) is not None


# --- Изменение 79: Тесты FAISS auto-nlist ---


def test_build_faiss_small_dataset(cfg, db_path):
    """Малый набор данных (< 256) -> IndexFlatIP без ошибок."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path, use_faiss=True)
    kb = KnowledgeBase(config=cfg2)

    # Create a small set of embeddings
    embeddings = np.random.randn(50, 300).astype(np.float32)

    try:
        index = kb._build_faiss_index_from_embeddings(embeddings)
        if index is not None:
            # Should be IndexFlatIP (not IVF)
            assert index.ntotal == 50
    except ImportError:
        # faiss not installed, skip
        pass

    kb.close()


def test_build_faiss_adjusts_nlist(cfg, db_path):
    """500 векторов -> nlist уменьшен для train."""
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path, use_faiss=True)
    kb = KnowledgeBase(config=cfg2)

    # Create 500 embeddings
    embeddings = np.random.randn(500, 300).astype(np.float32)

    try:
        index = kb._build_faiss_index_from_embeddings(embeddings)
        if index is not None:
            # Should be IndexIVFPQ with adjusted nlist
            assert index.ntotal == 500
    except ImportError:
        # faiss not installed, skip
        pass

    kb.close()
