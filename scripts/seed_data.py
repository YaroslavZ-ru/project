import logging
from pathlib import Path
import sqlite3
import sys

logger = logging.getLogger(__name__)

CONCEPTS_DATA = [
    {
        "id": "concept_001",
        "term": "ключ гаечный",
        "domain": "слесарный инструмент",
        "parameters": [
            {
                "name": "size_mm",
                "label_ru": "Размер",
                "type": "float",
                "description": "Под ключа в мм",
                "unit": "мм",
            },
            {
                "name": "material",
                "label_ru": "Материал",
                "type": "string",
                "description": "Материал изготовления",
            },
            {
                "name": "torque_nm",
                "label_ru": "Момент затяжки",
                "type": "float",
                "description": "Максимальный момент",
                "unit": "Н·м",
            },
        ],
    },
    {
        "id": "concept_002",
        "term": "ключ разводной",
        "domain": "слесарный инструмент",
        "parameters": [
            {
                "name": "size_range_mm",
                "label_ru": "Диапазон размеров",
                "type": "string",
                "description": "Мин-макс размер в мм",
            },
            {
                "name": "material",
                "label_ru": "Материал",
                "type": "string",
                "description": "Материал изготовления",
            },
        ],
    },
    {
        "id": "concept_003",
        "term": "ключ скрипичный",
        "domain": "музыка",
        "parameters": [
            {
                "name": "clef_type",
                "label_ru": "Тип ключа",
                "type": "enum",
                "description": "Вид музыкального ключа",
                "enum_values": '["\u0441\u043a\u0440\u0438\u043f\u0438\u0447\u043d\u044b\u0439","\u0431\u0430\u0441\u043e\u0432\u044b\u0439","\u0430\u043b\u044c\u0442\u043e\u0432\u044b\u0439"]',
            },
            {
                "name": "staff_position",
                "label_ru": "Позиция на нотном стане",
                "type": "integer",
                "description": "Номер линии",
            },
        ],
    },
]


def seed(config, force: bool = False) -> None:
    conn = sqlite3.connect(str(config.db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    if not force:
        cursor.execute("SELECT COUNT(*) FROM concepts")
        if cursor.fetchone()[0] > 0:
            logger.info("База содержит данные. Используйте --force для перезаписи.")
            conn.close()
            return

    if force:
        conn.execute("DELETE FROM relations")
        conn.execute("DELETE FROM parameters")
        conn.execute("DELETE FROM concepts")
        conn.commit()
        logger.info("Таблицы очищены.")

    from src.embeddings import FastTextWrapper
    from src.knowledge_base import KnowledgeBase
    from src.lemmatizer import Lemmatizer
    from src.synonyms import SynonymDict

    Lemmatizer(cache_size=config.cache_lemma_size)
    synonym_dict = SynonymDict(config.synonyms_path)
    fallback_path = (
        Path(config.fallback_embeddings_path) if config.fallback_embeddings_path else None
    )
    embedding_model = FastTextWrapper(
        model_path=Path(config.fasttext_model_path),
        fallback_path=fallback_path,
        cache_size=config.word_vector_cache_size,
    )
    kb = KnowledgeBase(config=config, embedding_model=embedding_model, synonym_dict=synonym_dict)

    try:
        for concept in CONCEPTS_DATA:
            embedding = kb.compute_concept_embedding(concept["term"])
            blob = embedding.astype("<f4").tobytes()
            cursor.execute(
                "INSERT OR IGNORE INTO concepts (id, term, domain, embedding) VALUES (?,?,?,?)",
                (concept["id"], concept["term"], concept["domain"], blob),
            )
            for p in concept["parameters"]:
                cursor.execute(
                    "INSERT OR IGNORE INTO parameters"
                    " (concept_id, name, label_ru, type, description, unit, enum_values)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (
                        concept["id"],
                        p["name"],
                        p["label_ru"],
                        p.get("type", "string"),
                        p.get("description", ""),
                        p.get("unit"),
                        p.get("enum_values"),
                    ),
                )
        conn.commit()
        logger.info("Вставлено: %d понятий", len(CONCEPTS_DATA))
    finally:
        kb.close()
        conn.close()


if __name__ == "__main__":
    _root = Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    import argparse

    from src.config import Config

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Наполнение БД тестовыми данными")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--config", default="configs/config.json")
    args = parser.parse_args()
    cfg = Config.from_json(args.config, project_root=_root)
    seed(cfg, force=args.force)
