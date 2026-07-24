"""scripts/export_kb.py -- экспорт knowledge_base.db в JSON или CSV.

Формат вывода совместим с update_kb.py для реимпорта (JSON).

Использование:
    python -m scripts.export_kb
    python -m scripts.export_kb --format csv --output data/export.csv
    python -m scripts.export_kb --output data/backup.json
"""

import contextlib
import csv
import json
import logging
from pathlib import Path
import sqlite3
import sys

logger = logging.getLogger(__name__)


def export_kb(config, output_path: Path) -> dict:
    """Экспортировать все концепты из SQLite в JSON-файл.

    Формат вывода совместим с update_kb.py (круговой экспорт → импорт).

    Args:
        config:      конфигурация (Config).
        output_path: путь для сохранения JSON.

    Returns:
        Словарь статистики:
        {"concepts_count": N, "parameters_count": M, "saved_to": str(output_path)}
        Или {"error": str} при ошибке.
    """
    try:
        conn = sqlite3.connect(str(config.db_path))
        conn.row_factory = sqlite3.Row

        concept_rows = conn.execute("SELECT id, term, domain FROM concepts ORDER BY id").fetchall()

        concepts_list = []
        total_params = 0

        for concept_row in concept_rows:
            concept_id = concept_row["id"]
            param_rows = conn.execute(
                "SELECT name, label_ru, type, description, unit, enum_values, confidence"
                " FROM parameters WHERE concept_id = ? ORDER BY id",
                (concept_id,),
            ).fetchall()

            parameters = []
            for pr in param_rows:
                enum_val = pr["enum_values"]
                if enum_val:
                    with contextlib.suppress(json.JSONDecodeError, TypeError):
                        enum_val = json.loads(enum_val)
                else:
                    enum_val = None

                parameters.append(
                    {
                        "name": pr["name"],
                        "label_ru": pr["label_ru"],
                        "type": pr["type"],
                        "description": pr["description"],
                        "unit": pr["unit"],
                        "enum_values": enum_val,
                        "confidence": pr["confidence"],
                    }
                )

            total_params += len(parameters)
            concepts_list.append(
                {
                    "id": concept_id,
                    "term": concept_row["term"],
                    "domain": concept_row["domain"],
                    "parameters": parameters,
                }
            )

        conn.close()

        # Создать директорию если не существует
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(concepts_list, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        concepts_count = len(concepts_list)
        stats = {
            "concepts_count": concepts_count,
            "parameters_count": total_params,
            "saved_to": str(output_path),
        }
        logger.info(
            "Экспорт: %d концептов, %d параметров -> %s",
            concepts_count,
            total_params,
            output_path,
        )
        return stats

    except PermissionError as exc:
        logger.error("Нет прав доступа к файлу: %s", exc)
        return {"error": "permission_denied"}
    except sqlite3.Error as exc:
        logger.error("Ошибка SQLite: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.error("Неожиданная ошибка: %s", exc)
        return {"error": str(exc)}


def export_kb_csv(config, output_path: Path) -> dict:
    """Экспортировать все концепты из SQLite в CSV-файл.

    Формат: одна строка на параметр, заголовки: concept_id, term, domain,
    param_name, param_label_ru, param_type, param_unit,
    param_description, param_enum_values.

    Args:
        config:      конфигурация (Config).
        output_path: путь для сохранения CSV.

    Returns:
        Словарь статистики.
    """
    try:
        conn = sqlite3.connect(str(config.db_path))
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            "SELECT c.id, c.term, c.domain,"
            "       p.name, p.label_ru, p.type, p.unit,"
            "       p.description, p.enum_values"
            " FROM concepts c"
            " LEFT JOIN parameters p ON c.id = p.concept_id"
            " ORDER BY c.id, p.id"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        header = [
            "concept_id", "term", "domain", "param_name", "param_label_ru",
            "param_type", "param_unit", "param_description", "param_enum_values",
        ]

        concepts_count = 0
        params_count = 0
        seen_concepts: set = set()

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for row in cursor:
                cid = row["id"]
                if cid not in seen_concepts:
                    seen_concepts.add(cid)
                    concepts_count += 1

                enum_val = row["enum_values"] or ""

                writer.writerow([
                    cid,
                    row["term"],
                    row["domain"] or "",
                    row["name"] or "",
                    row["label_ru"] or "",
                    row["type"] or "",
                    row["unit"] or "",
                    row["description"] or "",
                    enum_val,
                ])

                if row["name"]:
                    params_count += 1

        conn.close()

        stats = {
            "concepts_count": concepts_count,
            "parameters_count": params_count,
            "saved_to": str(output_path),
        }
        logger.info(
            "CSV-экспорт: %d концептов, %d параметров -> %s",
            concepts_count,
            params_count,
            output_path,
        )
        return stats

    except PermissionError as exc:
        logger.error("Нет прав доступа к файлу: %s", exc)
        return {"error": "permission_denied"}
    except sqlite3.Error as exc:
        logger.error("Ошибка SQLite: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.error("Неожиданная ошибка: %s", exc)
        return {"error": str(exc)}


if __name__ == "__main__":
    import argparse

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.config import Config

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="AI-Terminator: экспорт БД концептов в JSON или CSV",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/export_kb.json",
        help="Путь для сохранения (default: data/export_kb.json)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="json",
        choices=["json", "csv"],
        help="Формат экспорта: json или csv (default: json)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.json",
        help="Путь к файлу конфигурации (default: configs/config.json)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    try:
        cfg = Config.from_json(args.config, project_root=project_root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Ошибка при загрузке конфига: {exc}")
        sys.exit(1)

    output_path = project_root / args.output

    if args.format == "csv":
        if args.output == "data/export_kb.json":
            output_path = project_root / "data" / "export_kb.csv"
        result = export_kb_csv(cfg, output_path)
    else:
        result = export_kb(cfg, output_path)

    if "error" in result:
        print(f"Ошибка: {result['error']}")
        sys.exit(1)

    print(
        f"Экспорт завершён ({args.format}): {result['concepts_count']} концептов, "
        f"{result['parameters_count']} параметров -> {result['saved_to']}"
    )
