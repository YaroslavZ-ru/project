import json
import pytest
from src.synonyms import SynonymDict


@pytest.fixture
def syn_path(tmp_path):
    data = {
        "\u043a\u043b\u044e\u0447": [
            {"word": "\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442", "weight": 0.8},
            {"word": "\u043e\u0442\u043c\u044b\u0447\u043a\u0430", "weight": 0.4}
        ],
        "\u0442\u0435\u0445\u043d\u0438\u043a\u0430": [{"word": "\u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c", "weight": 0.7}]
    }
    p = tmp_path / "syn.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_get_synonyms(syn_path):
    sd = SynonymDict(syn_path)
    assert sd.get_synonyms("\u043a\u043b\u044e\u0447") == ["\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442", "\u043e\u0442\u043c\u044b\u0447\u043a\u0430"]

def test_max_synonyms(syn_path):
    sd = SynonymDict(syn_path)
    assert sd.get_synonyms("\u043a\u043b\u044e\u0447", max_synonyms=1) == ["\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442"]

def test_unknown_lemma(syn_path):
    sd = SynonymDict(syn_path)
    assert sd.get_synonyms("\u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e") == []

def test_missing_file(tmp_path):
    sd = SynonymDict(tmp_path / "nofile.json")
    assert sd.get_synonyms("\u043a\u043b\u044e\u0447") == []

def test_old_format_rejected(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"\u043a\u043b\u044e\u0447": ["\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442"]}), encoding="utf-8")
    sd = SynonymDict(p)
    assert sd.get_synonyms("\u043a\u043b\u044e\u0447") == []