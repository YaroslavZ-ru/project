"""tests/test_config.py -- тесты класса Config."""

import json
from pathlib import Path

import pytest

from src.config import Config

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "config.json"


def test_load_real_config():
    """Config загружается без ошибок и db_path -- абсолютный путь."""
    cfg = Config.from_json(CONFIG_PATH, project_root=PROJECT_ROOT)
    assert cfg.db_path.is_absolute()
    assert cfg.min_confidence == 0.3
    assert cfg.log_level == "INFO"
    assert isinstance(cfg.generative_keywords, list)
    assert len(cfg.generative_keywords) > 0


def test_min_confidence_out_of_range(tmp_path):
    """ValueError если min_confidence > 1."""
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data["min_confidence"] = 1.5
    bad = tmp_path / "config.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="min_confidence"):
        Config.from_json(bad, project_root=PROJECT_ROOT)


def test_missing_max_candidates(tmp_path):
    """ValueError если отсутствует max_candidates."""
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    del data["max_candidates"]
    bad = tmp_path / "config.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="max_candidates"):
        Config.from_json(bad, project_root=PROJECT_ROOT)


def test_log_level_lowercase(tmp_path):
    """ValueError если log_level в нижнем регистре."""
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data["log_level"] = "info"
    bad = tmp_path / "config.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="log_level"):
        Config.from_json(bad, project_root=PROJECT_ROOT)


def test_file_not_found():
    """FileNotFoundError если файл не существует."""
    with pytest.raises(FileNotFoundError, match="конфигурации"):
        Config.from_json("configs/nonexistent.json", project_root=PROJECT_ROOT)
