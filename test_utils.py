"""tests/test_utils.py -- тесты утилит общего назначения.

Включает тесты JSONFormatter (изм. 65).
"""

import json
import logging
from io import StringIO

import pytest

from src.utils import JSONFormatter, safe_truncate, timed, unique_ordered


# --- Тесты safe_truncate ---


def test_safe_truncate_short():
    assert safe_truncate("hello", 10) == "hello"


def test_safe_truncate_long():
    assert safe_truncate("hello world", 8) == "hello..."


def test_safe_truncate_none():
    assert safe_truncate(None, 10) == ""


def test_safe_truncate_custom_suffix():
    assert safe_truncate("hello world", 8, suffix="..") == "hello .."


# --- Тесты unique_ordered ---


def test_unique_ordered_basic():
    assert unique_ordered([1, 2, 1, 3]) == [1, 2, 3]


def test_unique_ordered_empty():
    assert unique_ordered([]) == []


# --- Изменение 65: Тесты JSONFormatter ---


class TestJSONFormatter:
    def test_basic_output(self):
        """Базовый вывод — валидный JSON с обязательными полями."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["msg"] == "Test message"
        assert "ts" in data

    def test_extra_fields(self):
        """Дополнительные контекстные поля попадают в JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Query processed",
            args=(),
            exc_info=None,
        )
        record.term = "ключ"
        record.request_id = "abc123"
        record.status = "ok"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["term"] == "ключ"
        assert data["request_id"] == "abc123"
        assert data["status"] == "ok"

    def test_exception_included(self):
        """Исключение включается в JSON."""
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "test error" in data["exception"]

    def test_output_is_valid_json(self):
        """Каждая строка — валидный JSON (не ломается при спецсимволах)."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg='Сообщение с "кавычками" и \n переносом',
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)  # Не должно выбросить исключение
        assert data["msg"] == 'Сообщение с "кавычками" и \n переносом'

    def test_utf8_preserved(self):
        """Русский текст сохраняется корректно."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="ai_terminator",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Запуск пайплайна: термин 'ключ'",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "Запуск пайплайна" in output
        data = json.loads(output)
        assert data["msg"] == "Запуск пайплайна: термин 'ключ'"

    def test_record_without_extra_fields(self):
        """Запись без доп. полей — только базовые ключи."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="simple",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        # Не должно быть term, request_id и т.д.
        assert "term" not in data
        assert "request_id" not in data


# --- M-15: Декоратор timed логирует время даже при исключении ---


def test_timed_logs_even_on_exception(caplog):
    """Декоратор timed логирует время даже при исключении."""
    test_logger = logging.getLogger("test_timed")

    @timed(test_logger, "test_func")
    def failing_func():
        raise ValueError("test error")

    with caplog.at_level(logging.DEBUG, logger="test_timed"):
        with pytest.raises(ValueError, match="test error"):
            failing_func()

    assert any("test_func" in record.message for record in caplog.records)
