"""scripts/update_kb.py -- импорт новых понятий в knowledge_base.db.

Поддерживает форматы JSON и CSV.
Вычисляет эмбеддинги через KnowledgeBase.compute_concept_embedding.
Запуск: python -m scripts.update_kb --file <path>
"""

import contextlib
import csv
import json
import logging
from pathlib import Path
import sqlite3

from src.config import Config
from src.embeddings import FastTextWrapper
from src.knowledge_base import KnowledgeBase
from src.lemmatizer import Lemmatizer
from src.synonyms import SynonymDict

logger = logging.getLogger(__name__)


def validate_concept(concept: dict) -> list[str]:
    """Проверяет структуру концепта и возвращает список ошибок.

    Args:
        concept: словарь с данными концепта.

    Returns:
        Пустой список = концепт валиден, либо список строк с описанием ошибок.
    """
    errors: list[str] = []
    _VALID_PARAM_TYPES = {"string", "integer", "float", "boolean", "enum"}

    # id
    cid = concept.get("id")
    if not cid or not isinstance(cid, str) or cid != cid.strip():
        errors.append("Поле 'id' обязательно, должно быть непустой строкой без пробелов по краям")

    # term
    term = concept.get("term")
    if not term or not isinstance(term, str) or not term.strip():
        errors.append("Поле 'term' обязательно и должно быть непустым")

    # parameters
    params = concept.get("parameters")
    if params is not None:
        if not isinstance(params, list):
            errors.append("Поле 'parameters' должно быть списком")
        else:
            for i, p in enumerate(params):
                if not p.get("name") or not str(p["name"]).strip():
                    errors.append(f"Параметр [{i}]: 'name' обязателен и не должен быть пустым")
                if not p.get("label_ru") or not str(p["label_ru"]).strip():
                    errors.append(f"Параметр [{i}]: 'label_ru' обязателен и не должен быть пустым")
                ptype = p.get("type")
                if ptype is not None and ptype not in _VALID_PARAM_TYPES:
                    errors.append(
                        f"Параметр [{i}]: недопустимый type={ptype!r}. "
                        f"Допустимы: {_VALID_PARAM_TYPES}"
                    )
    return errors


def load_concepts_from_json(path: Path) -> list[dict]:
    """Загружает концепты из JSON-файла.

    Args:
        path: путь к JSON-файлу.

    Returns:
        Список словарей или [] при ошибке.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Файл не найден: %s", path)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.error("Ошибка чтения файла %s: %s", path, exc)
        return []

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("Ошибка JSON в %s: %s", path, exc)
        return []

    if not isinstance(data, list):
        logger.error("Корневой элемент JSON должен быть списком, получен %s", type(data).__name__)
        return []

    return data


def load_concepts_from_csv(path: Path) -> list[dict]:
    """Загружает концепты из CSV-файла.

    Формат заголовка:
    id,term,domain,param_name,param_label_ru,param_type,param_description,param_unit

    Строки с одинаковым id группируются в один концепт.

    Args:
        path: путь к CSV-файлу.

    Returns:
        Список словарей или [] при ошибке.
    """
    try:
        concepts_map: dict[str, dict] = {}
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("id", "").strip()
                if not cid:
                    continue
                if cid not in concepts_map:
                    concepts_map[cid] = {
                        "id": cid,
                        "term": row.get("term", "").strip(),
                        "domain": row.get("domain", "").strip() or None,
                        "parameters": [],
                    }
                param_name = row.get("param_name", "").strip()
                if param_name:
                    concepts_map[cid]["parameters"].append(
                        {
                            "name": param_name,
                            "label_ru": row.get("param_label_ru", "").strip(),
                            "type": row.get("param_type", "string").strip() or "string",
                            "description": row.get("param_description", "").strip() or None,
                            "unit": row.get("param_unit", "").strip() or None,
                            "enum_values": None,
                        }
                    )
        return list(concepts_map.values())
    except Exception as exc:  # noqa: BLE001
        logger.error("Ошибка чтения CSV %s: %s", path, exc)
        return []


def update_from_concepts(
    concepts: list[dict],
    config: Config,
    force: bool = False,
) -> dict:
    """Добавляет или обновляет концепты в БД.

    Вычисляет эмбеддинги через KnowledgeBase.

    Args:
        concepts: список концептов.
        config:   Config.
        force:    если True -- обновлять существующие.

    Returns:
        {"inserted": int, "updated": int, "skipped": int, "errors": int}
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}

    # Инициализация компонентов для эмбеддингов
    Lemmatizer(cache_size=config.cache_lemma_size)
    synonym_dict = SynonymDict(json_path=config.synonyms_path)
    fallback_path = config.fallback_embeddings_path if config.fallback_embeddings_path else None
    embedding_model = FastTextWrapper(
        model_path=config.fasttext_model_path,
        fallback_path=fallback_path,
        cache_size=config.word_vector_cache_size,
    )
    kb = KnowledgeBase(
        config=config,
        embedding_model=embedding_model,
        synonym_dict=synonym_dict,
    )

    try:
        conn = sqlite3.connect(str(config.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
    except sqlite3.Error as exc:
        logger.error("Ошибка подключения к БД: %s", exc)
        return stats

    try:
        for concept in concepts:
            errors_list = validate_concept(concept)
            if errors_list:
                cid = concept.get("id", "<unknown>")
                logger.warning("Невалидный концепт %r: %s", cid, errors_list)
                stats["errors"] += 1
                continue

            cid = concept["id"]
            cursor.execute("SELECT id FROM concepts WHERE id=?", (cid,))
            exists = cursor.fetchone() is not None

            if exists and not force:
                stats["skipped"] += 1
                continue

            # Вычисляем эмбеддинг
            try:
                emb = kb.compute_concept_embedding(concept["term"])
            except Exception as exc:  # noqa: BLE001
                logger.error("Ошибка вычисления эмбеддинга для %r: %s", cid, exc)
                stats["errors"] += 1
                continue

            blob = emb.astype("<f4").tobytes()
            domain = concept.get("domain") or None
            term_val = concept["term"]

            if not exists:
                cursor.execute(
                    "INSERT INTO concepts (id, term, domain, embedding) VALUES (?,?,?,?)",
                    (cid, term_val, domain, blob),
                )
                stats["inserted"] += 1
            else:  # force=True
                cursor.execute(
                    "UPDATE concepts SET term=?, domain=?, embedding=? WHERE id=?",
                    (term_val, domain, blob, cid),
                )
                cursor.execute("DELETE FROM parameters WHERE concept_id=?", (cid,))
                stats["updated"] += 1

            # Вставляем параметры
            for p in concept.get("parameters", []):
                enum_val = p.get("enum_values")
                if isinstance(enum_val, list):
                    enum_val = json.dumps(enum_val, ensure_ascii=False)
                elif not enum_val:
                    enum_val = None
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO parameters
                        (concept_id, name, label_ru, type, description, unit, enum_values)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        cid,
                        p.get("name", ""),
                        p.get("label_ru", ""),
                        p.get("type", "string"),
                        p.get("description") or None,
                        p.get("unit") or None,
                        enum_val,
                    ),
                )

        conn.commit()

    except sqlite3.Error as exc:
        logger.error("Ошибка SQLite: %s", exc)
        conn.rollback()
    finally:
        # Сброс кэша концептов в KnowledgeBase
        if hasattr(kb, "_concepts_cache"):
            kb._concepts_cache = None
        with contextlib.suppress(Exception):
            kb.close()
        conn.close()

    logger.info(
        "Импорт: inserted=%d updated=%d skipped=%d errors=%d",
        stats["inserted"],
        stats["updated"],
        stats["skipped"],
        stats["errors"],
    )
    return stats


if __name__ == "__main__":
    import argparse
    from pathlib import Path as _Path
    import sys

    _root = _Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    import logging as _logging

    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Импорт концептов в knowledge_base.db из JSON или CSV"
    )
    parser.add_argument("--file", required=True, help="Путь к файлу для импорта")
    parser.add_argument("--force", action="store_true", help="Обновлять существующие")
    parser.add_argument("--config", default="configs/config.json", help="Путь к конфигу")
    args = parser.parse_args()

    from src.config import Config as _Config

    try:
        cfg = _Config.from_json(args.config, project_root=_root)
    except Exception as e:
        print(f"Ошибка загрузки конфига: {e}", file=sys.stderr)
        sys.exit(1)

    input_path = _Path(args.file)
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        concepts = load_concepts_from_json(input_path)
    elif suffix == ".csv":
        concepts = load_concepts_from_csv(input_path)
    else:
        print(
            f"Неподдерживаемый формат файла: {suffix}. Ожидаются .json или .csv",
            file=sys.stderr,
        )
        sys.exit(1)

    if not concepts:
        print("Концепты не загружены или файл пустой.", file=sys.stderr)
        sys.exit(1)

    result = update_from_concepts(concepts, cfg, force=args.force)

    stat_str = " ".join(f"{k}={v}" for k, v in result.items())
    print(f"Результат: {stat_str}")

    if result["errors"] > 0:
        sys.exit(1)
