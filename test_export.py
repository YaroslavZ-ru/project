"""tests/test_export.py -- тесты экспорта KB в JSON и CSV (изм. 72)."""

import csv
import json
from pathlib import Path
import sqlite3

from scripts.export_kb import export_kb, export_kb_csv
from scripts.init_db import init_db

PROJECT_ROOT = Path(__file__).parent.parent


def _make_cfg(tmp_path):
    """Создать мок-конфиг с БД в tmp_path."""
    from types import SimpleNamespace

    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    return SimpleNamespace(db_path=str(db_path))


def _seed_data(db_path):
    """Вставить тестовые данные в БД."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO concepts (id,term,domain) VALUES (?,?,?)",
        ("c1", "ключ", "техника"),
    )
    conn.execute(
        "INSERT INTO concepts (id,term,domain) VALUES (?,?,?)",
        ("c2", "нота", "музыка"),
    )
    conn.execute(
        "INSERT INTO parameters (concept_id,name,label_ru,type,unit,description,enum_values)"
        " VALUES (?,?,?,?,?,?,?)",
        ("c1", "size", "Размер", "float", "mm", "Длина ключа", None),
    )
    conn.execute(
        "INSERT INTO parameters (concept_id,name,label_ru,type,unit,description,enum_values)"
        " VALUES (?,?,?,?,?,?,?)",
        ("c2", "pitch", "Высота ноты", "enum", None, None, json.dumps(["C", "D", "E"])),
    )
    conn.commit()
    conn.close()


# --- JSON экспорт ---


def test_export_json_creates_file(tmp_path):
    """JSON экспорт создаёт файл."""
    cfg = _make_cfg(tmp_path)
    _seed_data(cfg.db_path)
    output = tmp_path / "export.json"
    result = export_kb(cfg, output)
    assert "error" not in result
    assert output.exists()
    assert result["concepts_count"] == 2
    assert result["parameters_count"] == 2


def test_export_json_backward_compatibility(tmp_path):
    """Старый формат JSON по-прежнему работает."""
    cfg = _make_cfg(tmp_path)
    _seed_data(cfg.db_path)
    output = tmp_path / "export.json"
    result = export_kb(cfg, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 2
    terms = {c["term"] for c in data}
    assert "ключ" in terms
    assert "нота" in terms


# --- CSV экспорт ---


def test_export_csv_creates_file(tmp_path):
    """CSV экспорт создаёт файл с заголовком."""
    cfg = _make_cfg(tmp_path)
    _seed_data(cfg.db_path)
    output = tmp_path / "export.csv"
    result = export_kb_csv(cfg, output)
    assert "error" not in result
    assert output.exists()
    assert result["concepts_count"] == 2


def test_export_csv_format(tmp_path):
    """CSV содержит правильные столбцы и данные."""
    cfg = _make_cfg(tmp_path)
    _seed_data(cfg.db_path)
    output = tmp_path / "export.csv"
    export_kb_csv(cfg, output)

    with open(output, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == [
            "concept_id", "term", "domain", "param_name", "param_label_ru",
            "param_type", "param_unit", "param_description", "param_enum_values",
        ]
        rows = list(reader)
        assert len(rows) == 2
        # First row: c1/ключ with param
        assert rows[0][1] == "ключ"
        assert rows[0][3] == "size"
        # Second row: c2/нота with param
        assert rows[1][1] == "нота"
        assert rows[1][3] == "pitch"
        assert rows[1][8]  # enum_values as JSON string


def test_export_csv_no_params(tmp_path):
    """Понятие без параметров: одна строка с пустыми param_* полями."""
    cfg = _make_cfg(tmp_path)
    conn = sqlite3.connect(cfg.db_path)
    conn.execute(
        "INSERT INTO concepts (id,term,domain) VALUES (?,?,?)",
        ("c1", "тест", "домен"),
    )
    conn.commit()
    conn.close()
    output = tmp_path / "export.csv"
    export_kb_csv(cfg, output)

    with open(output, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0][1] == "тест"
        assert rows[0][3] == ""  # param_name is empty
