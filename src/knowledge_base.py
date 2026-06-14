from collections import deque
import json
import logging
from pathlib import Path
import sqlite3
import time

import numpy as np

from src.lemmatizer import Lemmatizer

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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._conn.close()

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
                    "id": cid,
                    "term": row["term"],
                    "domain": row["domain"],
                    "embedding": self._blob_to_vector(row["embedding"]),
                    "parameters": [],
                }
            if row["name"] is not None:
                param = {
                    "name": row["name"],
                    "label_ru": row["label_ru"],
                    "type": row["type"],
                    "description": row["description"] or "",
                    "unit": row["unit"],
                    "enum_values": self._parse_enum(row["enum_values"]),
                    "confidence": float(row["confidence"] or 1.0),
                    "source": "knowledge_base",
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

    def load_domain_centroids(self, centroids_path: str | None = None) -> dict:
        """Загрузить центроиды доменов из JSON-файла.

        Args:
            centroids_path: путь к JSON-файлу. Если None — из конфига.

        Returns:
            dict {domain: np.ndarray float32} или пустой dict.
        """
        raw = centroids_path or getattr(self._config, "domain_centroids_path", "")
        if not raw:
            self.logger.debug("domain_centroids_path не задан")
            return {}
        path = Path(raw)
        if not path.exists():
            self.logger.debug("Файл центроидов не найден: %s", path)
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = {domain: np.array(vec, dtype=np.float32) for domain, vec in data.items()}
            self.logger.info("Загружено %d центроидов доменов", len(result))
            return result
        except Exception as exc:
            self.logger.error("Ошибка загрузки центроидов: %s", exc)
            return {}

    def get_concept_relations(
        self,
        concept_id: str,
        relation_types: list[str] | None = None,
        max_depth: int = 1,
    ) -> list[dict]:
        """Получить родственные концепты через таблицу relations (BFS).

        Args:
            concept_id:     id концепта-источника.
            relation_types: список типов. None — все типы.
            max_depth:      глубина обхода.

        Returns:
            list[dict] с полями concept_id, term, domain, relation_type, depth, embedding.
        """
        try:
            queue: deque = deque([(concept_id, 0)])
            visited: set = {concept_id}
            results: list[dict] = []
            with sqlite3.connect(str(self._config.db_path)) as conn:
                while queue:
                    curr_id, depth = queue.popleft()
                    if depth >= max_depth:
                        continue
                    if relation_types:
                        placeholders = ",".join("?" * len(relation_types))
                        query = (
                            "SELECT r.target_concept_id, r.relation_type, r.confidence,"
                            " c.term, c.domain, c.embedding"
                            " FROM relations r JOIN concepts c ON c.id = r.target_concept_id"
                            f" WHERE r.source_concept_id = ? AND r.relation_type IN ({placeholders})"
                        )
                        params = (curr_id, *relation_types)
                    else:
                        query = (
                            "SELECT r.target_concept_id, r.relation_type, r.confidence,"
                            " c.term, c.domain, c.embedding"
                            " FROM relations r JOIN concepts c ON c.id = r.target_concept_id"
                            " WHERE r.source_concept_id = ?"
                        )
                        params = (curr_id,)
                    for row in conn.execute(query, params):
                        target_id, rel_type, confidence, term, domain, emb_bytes = row
                        if target_id in visited:
                            continue
                        visited.add(target_id)
                        queue.append((target_id, depth + 1))
                        try:
                            emb = (
                                np.frombuffer(emb_bytes, dtype=np.float32)
                                if emb_bytes
                                else np.zeros(300, dtype=np.float32)
                            )
                        except Exception:
                            emb = np.zeros(300, dtype=np.float32)
                        results.append(
                            {
                                "concept_id": target_id,
                                "term": term,
                                "domain": domain,
                                "relation_type": rel_type,
                                "confidence": confidence,
                                "depth": depth + 1,
                                "embedding": emb,
                            }
                        )
            return results
        except sqlite3.Error as exc:
            self.logger.error("Ошибка get_concept_relations: %s", exc)
            return []

    def _search_with_relations(
        self,
        query_vector: np.ndarray,
        direct_results: list,
        min_confidence: float,
        max_candidates: int,
    ) -> list:
        """Расширить результаты поиска через граф отношений.

        Args:
            query_vector:   нормализованный вектор запроса.
            direct_results: прямые результаты поиска.
            min_confidence: порог similarity.
            max_candidates: макс. кандидатов.

        Returns:
            Расширенный список кандидатов.
        """
        if not getattr(self._config, "use_relations", False):
            return direct_results
        max_depth = getattr(self._config, "relation_max_depth", 1)
        decay_factor = getattr(self._config, "relation_decay_factor", 0.5)
        extended = list(direct_results)
        seen_ids = {c["concept_id"] for c in extended if "concept_id" in c}
        for c in direct_results:
            relations = self.get_concept_relations(c.get("concept_id", ""), max_depth=max_depth)
            for rel in relations:
                rel_id = rel["concept_id"]
                if rel_id in seen_ids:
                    continue
                rel_emb = rel["embedding"]
                if np.all(rel_emb == 0):
                    continue
                rel_sim = float(np.dot(query_vector, rel_emb.astype(np.float32)))
                weighted_sim = rel_sim * (decay_factor ** rel["depth"])
                if weighted_sim < min_confidence:
                    continue
                seen_ids.add(rel_id)
                extended.append(
                    {
                        "concept_id": rel_id,
                        "term": rel["term"],
                        "domain": rel["domain"],
                        "similarity": round(weighted_sim, 4),
                        "parameters": [],
                        "via_relation": rel["relation_type"],
                    }
                )
        extended.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
        return extended[:max_candidates]

    def get_closest_domain(
        self,
        query_vector: np.ndarray,
        domain_centroids: dict,
        min_threshold: float | None = None,
    ) -> str | None:
        """Найти домен с центроидом, ближайшим к вектору запроса.

        Args:
            query_vector:     нормализованный вектор запроса.
            domain_centroids: результат load_domain_centroids().
            min_threshold:    минимальный порог сходства. None = из конфига.

        Returns:
            Название домена или None если сходство ниже порога.
        """
        threshold = (
            min_threshold
            if min_threshold is not None
            else getattr(self._config, "domain_centroid_threshold", 0.3)
        )
        if not domain_centroids:
            return None
        best_domain, best_score = None, -1.0
        for domain, centroid in domain_centroids.items():
            score = float(np.dot(query_vector, centroid))
            if score > best_score:
                best_score = score
                best_domain = domain
        if best_score >= threshold:
            self.logger.debug("Ближайший центроид: %r (%.3f)", best_domain, best_score)
            return best_domain
        return None

    def _load_faiss_index_from_disk(self) -> bool:
        """Загрузить FAISS-индекс с диска (если задан faiss_index_path).

        Returns:
            True если индекс успешно загружен, False иначе.
        """
        faiss_path_str = getattr(self._config, "faiss_index_path", "")
        if not faiss_path_str:
            return False
        try:
            import faiss
        except ImportError:
            return False
        try:
            index_path = Path(faiss_path_str)
            id_map_path = index_path.with_suffix(".ids.json")
            if not index_path.exists() or not id_map_path.exists():
                self.logger.warning("FAISS: index or id map not found: %s", index_path)
                return False
            index = faiss.read_index(str(index_path))
            id_map = json.loads(id_map_path.read_text(encoding="utf-8"))
            concepts = self.get_all_concepts(use_cache=True)
            concepts_by_id = {c["id"]: c for c in concepts}
            ordered = [concepts_by_id[cid] for cid in id_map if cid in concepts_by_id]
            self._faiss_index = {"index": index, "concepts": ordered}
            self.logger.info("FAISS index loaded from disk: %d vectors", index.ntotal)
            return True
        except Exception as exc:
            self.logger.error("Error loading FAISS from disk: %s", exc)
            return False

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
                results.append(
                    {
                        "concept_id": c["id"],
                        "term": c["term"],
                        "domain": c["domain"],
                        "similarity": sim,
                        "parameters": c["parameters"],
                    }
                )
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
            if self._faiss_index is None and not self._load_faiss_index_from_disk():
                self._build_faiss_index(concepts)
            if self._faiss_index is not None:
                D, indices = self._faiss_index["index"].search(
                    query_vector.reshape(1, -1), max_candidates
                )
                fc = self._faiss_index["concepts"]
                results = [
                    {
                        "concept_id": fc[idx]["id"],
                        "term": fc[idx]["term"],
                        "domain": fc[idx]["domain"],
                        "similarity": float(d),
                        "parameters": fc[idx]["parameters"],
                    }
                    for d, idx in zip(D[0], indices[0], strict=False)
                    if idx != -1 and float(d) >= min_confidence
                ]
            else:
                results = self._linear_search(
                    query_vector, concepts, min_confidence, max_candidates
                )
        else:
            results = self._linear_search(query_vector, concepts, min_confidence, max_candidates)
        if len(results) < 3 and min_confidence > 0.2:
            self.logger.info("Расширяем поиск: %d кандидатов -> порог 0.2", len(results))
            results = self._linear_search(query_vector, concepts, 0.2, max_candidates)
        self.logger.debug("search: %d кандидатов за %.3fс", len(results), time.monotonic() - t0)
        if getattr(self._config, "use_relations", False) and results:
            results = self._search_with_relations(
                query_vector, results, min_confidence, max_candidates
            )
        return results
