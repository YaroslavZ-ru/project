import json

import pytest

from src.synonyms import SynonymDict


@pytest.fixture
def syn_path(tmp_path):
    data = {
        "ключ": [
            {"word": "инструмент", "weight": 0.8},
            {"word": "отмычка", "weight": 0.4},
        ],
        "техника": [{"word": "механизм", "weight": 0.7}],
    }
    p = tmp_path / "syn.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_get_synonyms(syn_path):
    sd = SynonymDict(syn_path)
    assert sd.get_synonyms("ключ") == ["инструмент", "отмычка"]


def test_max_synonyms(syn_path):
    sd = SynonymDict(syn_path)
    assert sd.get_synonyms("ключ", max_synonyms=1) == ["инструмент"]


def test_unknown_lemma(syn_path):
    sd = SynonymDict(syn_path)
    assert sd.get_synonyms("неизвестно") == []


def test_missing_file(tmp_path):
    sd = SynonymDict(tmp_path / "nofile.json")
    assert sd.get_synonyms("ключ") == []


def test_old_format_rejected(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"ключ": ["инструмент"]}), encoding="utf-8")
    sd = SynonymDict(p)
    assert sd.get_synonyms("ключ") == []


# --- M-10: Валидация веса синонимов ---


def test_invalid_weight_set_to_default(tmp_path):
    """Синоним с weight=-1 -> заменяется на 0.5."""
    data = {
        "ключ": [
            {"word": "инструмент", "weight": -1.0},
            {"word": "отмычка", "weight": 1.5},
        ]
    }
    p = tmp_path / "syn.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    sd = SynonymDict(p)
    # Both should be loaded with corrected weights (0.5)
    synonyms = sd.get_synonyms("ключ")
    assert len(synonyms) == 2
