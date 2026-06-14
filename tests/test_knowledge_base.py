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
    assert row[0] == "2"
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
