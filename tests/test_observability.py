"""tests/test_observability.py -- тесты модуля трассировки запросов."""

import json

from src.observability import (
    RequestStage,
    RequestTraceContext,
    format_log_record,
    generate_request_id,
    get_default_trace_context,
    is_json_serializable,
)


def test_generate_request_id_unique():
    """request_id должен быть уникальным для каждого вызова."""
    ids = {generate_request_id() for _ in range(100)}
    assert len(ids) == 100


def test_generate_request_id_length():
    """request_id должен быть hex-строкой длиной 32 символа."""
    rid = generate_request_id()
    assert len(rid) == 32
    assert all(c in "0123456789abcdef" for c in rid)


def test_request_trace_context_add_stage():
    """add_stage должен добавлять этап в список stages."""
    ctx = RequestTraceContext(request_id="test123")
    ctx.add_stage("preprocess", 0.05, {"lemmas": 3})
    assert len(ctx.stages) == 1
    assert ctx.stages[0].name == "preprocess"
    assert ctx.stages[0].duration_s == 0.05
    assert ctx.stages[0].details == {"lemmas": 3}


def test_request_trace_context_elapsed():
    """elapsed должен возвращать время с момента создания."""
    ctx = RequestTraceContext(request_id="test123")
    assert ctx.elapsed() >= 0


def test_request_trace_context_get_summary():
    """get_summary должен возвращать краткую сводку."""
    ctx = RequestTraceContext(request_id="test123")
    ctx.add_stage("preprocess", 0.05)
    ctx.add_stage("vectorize", 0.1)
    summary = ctx.get_summary()
    assert summary["request_id"] == "test123"
    assert summary["stages_count"] == 2
    assert len(summary["stages"]) == 2


def test_request_trace_context_to_dict():
    """to_dict должен возвращать полный словарь трассировки."""
    ctx = RequestTraceContext(request_id="test123")
    ctx.add_stage("preprocess", 0.05, {"lemmas": 3})
    d = ctx.to_dict()
    assert d["request_id"] == "test123"
    assert "elapsed_s" in d
    assert len(d["stages"]) == 1
    assert d["stages"][0]["name"] == "preprocess"


def test_get_default_trace_context_auto_id():
    """get_default_trace_context должен генерировать request_id, если не передан."""
    ctx = get_default_trace_context()
    assert len(ctx.request_id) == 32


def test_get_default_trace_context_custom_id():
    """get_default_trace_context должен использовать переданный request_id."""
    ctx = get_default_trace_context("custom_id")
    assert ctx.request_id == "custom_id"


def test_format_log_record():
    """format_log_record должен возвращать JSON-строку."""
    record = {"event": "test", "value": 42}
    result = format_log_record(record)
    parsed = json.loads(result)
    assert parsed["event"] == "test"
    assert parsed["value"] == 42


def test_is_json_serializable_true():
    """is_json_serializable должен возвращать True для сериализуемых значений."""
    assert is_json_serializable({"key": "value"})
    assert is_json_serializable([1, 2, 3])
    assert is_json_serializable("string")


def test_is_json_serializable_false():
    """is_json_serializable должен возвращать False для несериализуемых значений."""
    # set не сериализуется в JSON по умолчанию
    assert not is_json_serializable(set([1, 2, 3]))


def test_request_stage_dataclass():
    """RequestStage должен корректно создаваться."""
    stage = RequestStage(name="test", duration_s=0.1, details={"key": "value"})
    assert stage.name == "test"
    assert stage.duration_s == 0.1
    assert stage.details == {"key": "value"}
    assert stage.timestamp  # не пустая строка
