import sqlite3
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def init_db(db_path: str) -> None:
    p = Path(db_path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        logger.error("Ошибка создания папки %s: %s", p.parent, exc)
        sys.exit(1)

    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA foreign_keys = ON")

    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS concepts (
            id         TEXT PRIMARY KEY,
            term       TEXT NOT NULL,
            domain     TEXT,
            embedding  BLOB,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """
        CREATE TABLE IF NOT EXISTS parameters (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_id  TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            label_ru    TEXT NOT NULL,
            type        TEXT CHECK(type IN ('string','integer','float','boolean','enum')),
            description TEXT,
            unit        TEXT,
            enum_values TEXT,
            confidence  REAL DEFAULT 1.0
        )""",
        """
        CREATE TABLE IF NOT EXISTS relations (
            id                TEXT PRIMARY KEY,
            source_concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
            target_concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
            relation_type     TEXT NOT NULL CHECK(
                relation_type IN ('is_a','part_of','related_to','synonym')
            ),
            confidence  REAL DEFAULT 1.0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_concept_id, target_concept_id, relation_type)
        )""",
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key   TEXT PRIMARY KEY,
            value TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_concepts_domain       ON concepts(domain)",
        "CREATE INDEX IF NOT EXISTS idx_parameters_concept_id ON parameters(concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_relations_source      ON relations(source_concept_id)",
        "CREATE INDEX IF NOT EXISTS idx_relations_target      ON relations(target_concept_id)",
    ]

    try:
        for stmt in ddl_statements:
            conn.execute(stmt)
        conn.execute(
            "INSERT OR IGNORE INTO metadata (key,value) VALUES ('schema_version','2')"
        )
        conn.commit()
    except sqlite3.Error as exc:
        logger.error("Ошибка создания схемы: %s", exc)
        conn.close()
        sys.exit(1)

    conn.close()
    logger.info("База данных инициализирована: %s", db_path)


if __name__ == "__main__":
    _root = Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from src.config import Config
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Создание схемы БД")
    parser.add_argument("--config", default="configs/config.json")
    args = parser.parse_args()
    cfg = Config.from_json(args.config, project_root=_root)
    init_db(str(cfg.db_path))
