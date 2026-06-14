"""scripts/update_relations.py -- импорт отношений в relations.

Использование: python -m scripts.update_relations --file relations.json
"""
import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path
logger = logging.getLogger(__name__)
VALID_RELATION_TYPES = ["is_a","part_of","related_to","synonym"]

def validate_relation(rel: dict) -> list[str]:
    """Проверить поля одного отношения.
    Returns: список ошибок.
    """
    errors = []
    if not rel.get("source_id"):
        errors.append("пустой source_id")
    if not rel.get("target_id"):
        errors.append("пустой target_id")
    if rel.get("relation_type") not in VALID_RELATION_TYPES:
        errors.append(f"недопустимый relation_type: {rel.get('relation_type')} допустимые={VALID_RELATION_TYPES}")
    conf = rel.get("confidence",0)
    if not isinstance(conf,(int,float)) or not (0<=conf<=1):
        errors.append(f"неверный confidence: {conf}")
    return errors

def update_relations_from_json(path: Path, config, force: bool=False) -> dict:
    """Импортировать отношения из JSON в SQLite.
    Args:
        path:   путь к JSON-файлу.
        config: Config.
        force:  если True - удалить существующие отношения и вставить заново.
    Returns:
        {"inserted": int, "skipped": int, "errors": int}.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.error("Файл не найден: %s", path)
        return {"inserted":0,"skipped":0,"errors":1}
    except json.JSONDecodeError as exc:
        logger.error("Ошибка парсинга: %s", exc)
        return {"inserted":0,"skipped":0,"errors":1}
    inserted,skipped,errors=0,0,0
    try:
        conn=sqlite3.connect(str(config.db_path))
        if force:
            conn.execute("DELETE FROM relations")
            conn.commit()
        for rel in data:
            errs=validate_relation(rel)
            if errs:
                logger.warning("Ошибки: %s", errs)
                errors+=1
                continue
            src,tgt=rel["source_id"],rel["target_id"]
            if src==tgt:
                logger.warning("Цикл на себя: %s", src)
                skipped+=1
                continue
            exists_src=conn.execute("SELECT 1 FROM concepts WHERE id=?",([src])).fetchone()
            exists_tgt=conn.execute("SELECT 1 FROM concepts WHERE id=?",([tgt])).fetchone()
            if not exists_src or not exists_tgt:
                logger.warning("Концепт не найден src=%s tgt=%s", src, tgt)
                errors+=1
                continue
            cur=conn.execute(
                "INSERT OR IGNORE INTO relations(source_concept_id,target_concept_id,relation_type,confidence) VALUES(?,?,?,?)",
                (src,tgt,rel["relation_type"],float(rel.get("confidence",1.0)))
            )
            if cur.rowcount == 0:
                skipped += 1
            else:
                inserted += 1
        conn.commit()
        conn.close()
        logger.info("Отношения: inserted=%d skipped=%d errors=%d",inserted,skipped,errors)
        return {"inserted":inserted,"skipped":skipped,"errors":errors}
    except sqlite3.Error as exc:
        logger.error("Ошибка SQLite: %s",exc)
        return {"inserted":inserted,"skipped":skipped,"errors":errors+1}

if __name__=="__main__":
    sys.path.insert(0,str(Path(__file__).parent.parent))
    from src.config import Config
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(name)s %(message)s")
    parser=argparse.ArgumentParser(description="Импорт отношений в SQLite")
    parser.add_argument("--file",required=True)
    parser.add_argument("--config",default="configs/config.json")
    parser.add_argument("--force",action="store_true")
    args=parser.parse_args()
    try:
        cfg = Config.from_json(args.config, project_root=Path("."))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    result = update_relations_from_json(Path(args.file), cfg, force=args.force)
    print(f"inserted={result['inserted']} skipped={result['skipped']} errors={result['errors']}")