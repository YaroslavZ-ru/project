import pytest
from src.aggregation import aggregate_parameters, determine_context


def make_param(name, label="Парам", desc=""):
    return {"name": name, "label_ru": label, "type": "string", "description": desc, "confidence": 1.0, "source": "knowledge_base"}


Cands = [
    {"similarity": 0.9, "domain": "слесарный инструмент",
     "parameters": [make_param("material", "Материал"), make_param("size", "Размер")]},
    {"similarity": 0.7, "domain": "слесарный инструмент",
     "parameters": [make_param("material", "Материал")]},
]


def test_freq_affects_rank():
    result = aggregate_parameters(Cands, [], max_parameters=10)
    names = [p["name"] for p in result]
    assert names[0] == "material"  # freq=2 побеждает


def test_source_knowledge_base():
    result = aggregate_parameters(Cands, [], max_parameters=10)
    assert all(p["source"] == "knowledge_base" for p in result)


def test_confidence_normalized():
    result = aggregate_parameters(Cands, [], max_parameters=10)
    assert result[0]["confidence"] == pytest.approx(1.0)


def test_empty_candidates():
    assert aggregate_parameters([], [], max_parameters=10) == []


def test_determine_context_single_domain():
    cands = [{"domain": "музыка", "similarity": 0.8}]
    ctx = determine_context(cands)
    assert ctx["domain"] == "музыка"


def test_determine_context_multi_domain():
    cands = [
        {"domain": "музыка",   "similarity": 0.8},
        {"domain": "музыка",   "similarity": 0.7},
        {"domain": "техника", "similarity": 0.9},
    ]
    ctx = determine_context(cands)
    assert ctx["domain"] == "музыка"  # sum=1.5 > 0.9


def test_determine_context_empty():
    ctx = determine_context([])
    assert ctx["domain"] == "не определено"
    assert ctx["confidence"] == 0.0


def test_hint_match_affects_rank():
    cands = [{
        "similarity": 0.8,
        "domain": "тест",
        "parameters": [
            {"name": "material", "label_ru": "Материал изготовления", "description": "материал", "type": "string", "confidence": 1.0, "source": "kb"},
            {"name": "size",     "label_ru": "Размер дляноо",          "description": "размер",    "type": "float",  "confidence": 1.0, "source": "kb"},
        ]
    }]
    # подсказка "материал" даёт hint_match=1.0 для material
    result = aggregate_parameters(cands, hints_lemmas=[["материал"]], max_parameters=10)
    assert result[0]["name"] == "material"