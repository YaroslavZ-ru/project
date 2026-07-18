"""src/utils.py -- утилиты общего назначения AI-Terminator.

Модуль не импортирует ничего из src/ -- нет риска циклических импортов.
Использует только stdlib: logging, functools, time, json.
"""

from collections.abc import Callable
import functools
import json
import logging
import time
from typing import Any


def timed(logger: logging.Logger, label: str | None = None) -> Callable:
    """Параметризованный декоратор измерения времени выполнения функции.

    Логирует время на уровне DEBUG в формате "[label] завершён за X.XXXс".
    Использует finally -- время фиксируется даже при исключении.
    Сохраняет __name__, __doc__, __wrapped__ через functools.wraps.

    Args:
        logger: логгер для вывода времени.
        label:  метка для лога. Если None -- используется имя функции.

    Returns:
        Декоратор, оборачивающий переданную функцию.

    Example:
        log = logging.getLogger(__name__)

        @timed(log, "search")
        def search_similar(query):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tag = label or func.__name__
            start = time.monotonic()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.monotonic() - start
                logger.debug("[%s] завершён за %.3fс", tag, elapsed)

        return wrapper

    return decorator


def safe_truncate(
    text: str | None,
    max_len: int,
    suffix: str = "...",
) -> str:
    """Безопасно усекает строку до max_len символов.

    Args:
        text:    входная строка или None.
        max_len: максимальная длина результата (включая suffix).
        suffix:  добавляется в конец при усечении. По умолчанию "...".

    Returns:
        Усечённая строка. Если text is None или не str -- возвращает "".
        Если max_len <= 0 -- возвращает "".
        Если len(text) <= max_len -- возвращает text без изменений.

    Example:
        safe_truncate("hello world", 8)  # -> "hello..."
        safe_truncate(None, 10)          # -> ""
    """
    if not isinstance(text, str):
        return ""
    if max_len <= 0:
        return ""
    if len(text) <= max_len:
        return text
    cut = max(0, max_len - len(suffix))
    return text[:cut] + suffix


def unique_ordered(seq: list) -> list:
    """Удаляет дубликаты из списка, сохраняя порядок первого вхождения.

    Для hashable-элементов использует set (O(n)).
    Для unhashable-элементов (dict, list и т.п.) -- O(n^2) через "not in".

    Args:
        seq: исходный список (может быть пустым).

    Returns:
        Новый список без дубликатов с сохранением оригинального порядка.

    Example:
        unique_ordered([1, 2, 1, 3])          # -> [1, 2, 3]
        unique_ordered([{"a": 1}, {"a": 1}]) # -> [{"a": 1}]
    """
    seen: set = set()
    result: list = []
    for item in seq:
        try:
            if item not in seen:
                seen.add(item)
                result.append(item)
        except TypeError:
            # unhashable (dict, list и т.п.)
            if item not in result:
                result.append(item)
    return result


# --- Изменение 65: JSON-lines форматтер ---


class JSONFormatter(logging.Formatter):
    """Форматтер: каждая строка лога — валидный JSON-объект.

    Формат (JSON-lines):
        {"ts": "...", "level": "...", "logger": "...", "msg": "...", ...}

    Поддерживает дополнительные контекстные поля из record:
        term, hints, elapsed_ms, n_concepts, request_id, status, concept_id, path.
    """

    # Поля, которые извлекаются из record если присутствуют
    _CONTEXT_FIELDS = (
        "term", "hints", "elapsed_ms", "n_concepts",
        "request_id", "status", "concept_id", "path",
    )

    def _format_ts(self, record: logging.LogRecord) -> str:
        """Форматировать временную метку в ISO 8601 с микросекундами."""
        import datetime
        ct = self.converter(record.created)
        base = datetime.datetime(*ct[:6], tzinfo=datetime.timezone.utc)
        ms = int(record.msecs)
        return base.replace(microsecond=ms * 1000).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "ts": self._format_ts(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Добавляем дополнительные контекстные поля
        for key in self._CONTEXT_FIELDS:
            val = getattr(record, key, None)
            if val is not None:
                log_data[key] = val
        # Exc_info
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)
