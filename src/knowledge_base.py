import sqlite3
import json
import logging
import time
import numpy as np
from pathlib import Path
from src.config import Config
from src.lemmatizer import Lemmatizer
from src.synonyms import SynonymDict
from src.embeddings import FastTextWrapper

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self, config, embedding_model=None, synonym_dict=None):
        self._db_path = Path(config.db_path)
        self._config = config
        self._embedding_model = embedding_model
        self._synonym_dict = synonym_dict
        self._lemmatizer = Lemmatizer(cache_size=config.cache_lemma_size)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._concepts_cache = None
        self._faiss_index = None
        self.logger = logging.getLogger(__name__)

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def close(self): self._conn.close()

    def _blob_to_vector(self, blob):
        if blob is None:
            return np.zeros(300, dtype=np.float32)
        try:
            vec = np.frombuffer(blob, dtype="<f4").copy()
        except ValueError:
            self.logger.warning("Некорректный BLOB: %d байт (ожидалось 1200)", len(blob))
            return np.zeros(300, dtype=np.float32)
        if len(vec) != 300:
            self.logger.warning("Некорректный BLOB: %d байт (ожидалось 1200)", len(blob))
            return np.zeros(300, dtype=np.float32)
        return vec

    def _vector_to_blob(self, vector):
        return vector.astype("<f4").tobytes()

    def _parse_enum(self, value):
        if value is None or value.strip() == "":
            return None
        try:
            return json.loads(value)
        except Exception as exc:
            self.logger.warning("Ошибка парсинга enum_values %r: %s", value, exc)
            return None

    def get_all_concepts(self, use_cache=True):
        if use_cache and self._concepts_cache is not None:
            return self._concepts_cache
        cursor = self._conn.execute(
            "SELECT c.id, c.term, c.domain, c.embedding,"
            "       p.name, p.label_ru, p.type, p.description,"
            "       p.unit, p.enum_values, p.confidence"
            " FROM concepts c"
            " LEFT JOIN parameters p ON c.id = p.concept_id"
            " ORDER BY c.id, p.id"
        )
        concepts_dict = {}
        for row in cursor:
            cid = row["id"]
            if cid not in concepts_dict:
                concepts_dict[cid] = {
                    "id":         cid,
                    "term":       row["term"],
                    "domain":     row["domain"],
                    "embedding":  self._blob_to_vector(row["embedding"]),
                    "parameters": [],
                }
            if row["name"] is not None:
                param = {
                    "name":        row["name"],
                    "label_ru":    row["label_ru"],
                    "type":        row["type"],
                    "description": row["description"] or "",
                    "unit":        row["unit"],
                    "enum_values": self._parse_enum(row["enum_values"]),
                    "confidence":  float(row["confidence"] or 1.0),
                    "source":      "knowledge_base",
                }
                concepts_dict[cid]["parameters"].append(param)
        result = list(concepts_dict.values())
        if use_cache:
            self._concepts_cache = result
        return result

    def compute_concept_embedding(self, term):
        if self._embedding_model is None:
            raise RuntimeError("эмбеддинг-модель не задана")
        if self._synonym_dict is None:
            raise RuntimeError("словарь синонимов не задан")
        lemmas = self._lemmatizer.lemmatize_phrase(term)
        if not lemmas:
            return np.zeros(300, dtype=np.float32)
        term_w = 0.7 / len(lemmas)
        tokens_weights = [(lemma, term_w) for lemma in lemmas]
        lemmas_set = set(lemmas)
        synonyms_set = set()
        for lemma in lemmas:
            syns = self._synonym_dict.get_synonyms(
                lemma, max_synonyms=self._config.max_synonyms_per_token
            )
            synonyms_set.update(s for s in syns if s not in lemmas_set)
        if synonyms_set:
            syn_weight = 0.1 / len(synonyms_set)
            for syn in synonyms_set:
                tokens_weights.append((syn, syn_weight))
        weighted_sum = np.zeros(300, dtype=np.float64)
        for token, weight in tokens_weights:
            vec = self._embedding_model.get_phrase_vector(token)
            weighted_sum += weight * vec.astype(np.float64)
        norm = np.linalg.norm(weighted_sum)
        if norm > 1e-9:
            weighted_sum /= norm
        else:
            self.logger.warning("Нулевой вектор для термина: %s", term)
        return weighted_sum.astype("<f4")

    def update_all_embeddings(self):
        if self._embedding_model is None:
            raise RuntimeError("эмбеддинг-модель не задана")
        if self._synonym_dict is None:
            raise RuntimeError("словарь синонимов не задан")
        self._concepts_cache = None
        rows = self._conn.execute("SELECT id, term FROM concepts").fetchall()
        updated = 0
        for row in rows:
            blob = self._vector_to_blob(self.compute_concept_embedding(row["term"]))
            self._conn.execute("UPDATE concepts SET embedding=? WHERE id=?", (blob, row["id"]))
            updated += 1
        self._conn.commit()
        self._faiss_index = None
        self.logger.info("Пересчитано эмбеддингов: %d", updated)
        return updated

    def _build_faiss_index(self, concepts):
        try:
            import faiss
            index = faiss.IndexFlatIP(300)
            matrix = np.stack([c["embedding"] for c in concepts]).astype(np.float32)
            index.add(matrix)
            self._faiss_index = {"index": index, "concepts": concepts}
            self.logger.info("FAISS-индекс построен: %d", len(concepts))
        except ImportError:
            self.logger.warning("faiss не установлен. Переключение на линейный поиск.")
            self._config.use_faiss = False

    def _linear_search(self, query_vector, concepts, threshold, max_cand):
        results = []
        for c in concepts:
            sim = float(np.dot(query_vector, c["embedding"]))
            if sim >= threshold:
                results.append({
                    "concept_id": c["id"],
                    "term":       c["term"],
                    "domain":     c["domain"],
                    "similarity": sim,
                    "parameters": c["parameters"],
                })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:max_cand]

    def search_similar_concepts(self, query_vector, min_confidence=None, max_candidates=None):
        if min_confidence is None:
            min_confidence = self._config.min_confidence
        if max_candidates is None:
            max_candidates = self._config.max_candidates
        t0 = time.monotonic()
        norm_q = np.linalg.norm(query_vector)
        if norm_q < 1e-6:
            self.logger.warning("Нулевой query_vector, поиск пропущен")
            return []
        query_vector = (query_vector / norm_q).astype(np.float32)
        concepts = self.get_all_concepts()
        if not concepts:
            self.logger.warning("База пуста, поиск невозможен")
            return []
        if self._config.use_faiss and len(concepts) > self._config.faiss_threshold:
            if self._faiss_index is None:
                self._build_faiss_index(concepts)
            if self._faiss_index is not None:
                D, I = self._faiss_index["index"].search(
                    query_vector.reshape(1, -1), max_candidates
                )
                fc = self._faiss_index["concepts"]
                results = [
                    {
                        "concept_id": fc[i]["id"],
                        "term":       fc[i]["term"],
                        "domain":     fc[i]["domain"],
                        "similarity": float(d),
                        "parameters": fc[i]["parameters"],
                    }
                    for d, i in zip(D[0], I[0])
                    if i != -1 and float(d) >= min_confidence
                ]
            else:
                results = self._linear_search(query_vector, concepts, min_confidence, max_candidates)
        else:
            results = self._linear_search(query_vector, concepts, min_confidence, max_candidates)
        if len(results) < 3 and min_confidence > 0.2:
            self.logger.info("Расширяем поиск: %d кандидатов -> порог 0.2", len(results))
            results = self._linear_search(query_vector, concepts, 0.2, max_candidates)
        self.logger.debug("search: %d кандидатов за %.3fс", len(results), time.monotonic() - t0)
        return results