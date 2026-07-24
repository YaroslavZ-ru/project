"""tests/test_export.py -- тесты экспорта KB в JSON и CSV."""

import csv
import json
from pathlib import Path

import pytest

from scripts.init_db import init_db
from scripts.export_kb import export_kb, export_kb_csv
from src.config import Config
from src.knowledge_base import KnowledgeBase

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def cfg(tmp_path):
    c = Config.from_json("configs/config.json", project_root=PROJECT_ROOT)
    from dataclasses import replace

    return replace(c, db_path=str(tmp_path / "test.db"))


@pytest.fixture
def kb_with_data(cfg, tmp_path):
    """Создать KB с 2 понятиями и параметрами."""
    from dataclasses import replace

    db_path = str(tmp_path / "export_test.db")
    init_db(db_path)
    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)

    kb.save_concept(
        term="ключ гаечный",
        domain="слесарный инструмент",
        parameters=[
            {"name": "size_mm", "label_ru": "Размер (мм)", "type": "float"},
            {"name": "material", "label_ru": "Материал", "type": "string"},
        ],
    )
    kb.save_concept(
        term="ключ скрипичный",
        domain="музыка",
        parameters=[
            {"name": "clef_type", "label_ru": "Тип ключа", "type": "enum",
             "enum_values": ["скрипичный", "басовый"]},
        ],
    )
    return kb, cfg2, Path(db_path)


def test_export_json_creates_file(kb_with_data, tmp_path):
    """JSON-экспорт создаёт файл."""
    kb, cfg2, _ = kb_with_data
    output = tmp_path / "export.json"
    result = export_kb(cfg2, output)
    kb.close()

    assert "error" not in result
    assert output.exists()
    assert result["concepts_count"] == 2


def test_export_json_format(kb_with_data, tmp_path):
    """JSON-экспорт содержит правильный формат."""
    kb, cfg2, _ = kb_with_data
    output = tmp_path / "export.json"
    export_kb(cfg2, output)
    kb.close()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 2
    terms = {d["term"] for d in data}
    assert "ключ гаечный" in terms
    assert "ключ скрипичный" in terms
    wrench = [d for d in data if d["term"] == "ключ гаечный"][0]
    assert len(wrench["parameters"]) == 2


def test_export_csv_creates_file(kb_with_data, tmp_path):
    """CSV-экспорт создаёт файл."""
    kb, cfg2, _ = kb_with_data
    output = tmp_path / "export.csv"
    result = export_kb_csv(cfg2, output)
    kb.close()

    assert "error" not in result
    assert output.exists()
    assert result["concepts_count"] == 2


def test_export_csv_format(kb_with_data, tmp_path):
    """CSV-экспорт содержит правильные столбцы."""
    kb, cfg2, _ = kb_with_data
    output = tmp_path / "export.csv"
    export_kb_csv(cfg2, output)
    kb.close()

    with open(output, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    assert header == [
        "concept_id", "term", "domain", "param_name", "param_label_ru",
        "param_type", "param_unit", "param_description", "param_enum_values",
    ]
    assert len(rows) == 3  # 2 params + 1 param = 3 rows


def test_export_csv_backward_compatibility(cfg, tmp_path):
    """Старый формат JSON по-прежнему работает."""
    db_path = str(tmp_path / "compat.db")
    init_db(db_path)
    from dataclasses import replace

    cfg2 = replace(cfg, db_path=db_path)
    kb = KnowledgeBase(config=cfg2)
    kb.save_concept("тест", "домен")
    kb.close()

    output = tmp_path / "compat.json"
    result = export_kb(cfg2, output)

    assert "error" not in result
    data = json.loads(output.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["term"] == "тест"
