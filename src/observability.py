"""src/observability.py -- трассировка запросов AI-Terminator.

Предоставляет уникальный идентификатор запроса (request_id) и фиксирует
этапы прохождения через пайплайн для отладки и мониторинга.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RequestStage:
    """Один этап обработки запроса.

    Attributes:
        name:       название этапа (preprocess, vectorize, search и т.д.).
        duration_s: длительность этапа в секундах.
        details:    дополнительная информация об этапе.
        timestamp:  временная метка завершения этапа (ISO-8601).
    """

    name: str
    duration_s: float
    details: dict[str, Any] | None = None
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()))


@dataclass
class RequestTraceContext:
    """Контекст трассировки одного запроса.

    Attributes:
        request_id:  уникальный идентификатор запроса.
        started_at:  временная метка начала запроса (time.monotonic()).
        stages:      список пройденных этапов.
        metadata:    дополнительные метаданные запроса.
        log_level:   уровень логирования для этого запроса.
    """

    request_id: str
    started_at: float = field(default_factory=time.monotonic)
    stages: list[RequestStage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    log_level: str = "INFO"

    def add_stage(self, name: str, duration_s: float, details: dict[str, Any] | None = None) -> None:
        """Зафиксировать завершение этапа.

        Args:
            name:       название этапа.
            duration_s: длительность в секундах.
            details:    дополнительная информация.
        """
        stage = RequestStage(name=name, duration_s=duration_s, details=details)
        self.stages.append(stage)
        logger.debug(
            "Trace %s: stage=%s duration=%.4fs",
            self.request_id[:8],
            name,
            duration_s,
        )

    def get_summary(self) -> dict[str, Any]:
        """Вернуть краткую сводку трассировки.

        Returns:
            Словарь с request_id, total_duration_s, stages_count, stages.
        """
        total = self.elapsed()
        return {
            "request_id": self.request_id,
            "total_duration_s": round(total, 4),
            "stages_count": len(self.stages),
            "stages": [
                {
                    "name": s.name,
                    "duration_s": round(s.duration_s, 4),
                    "timestamp": s.timestamp,
                }
                for s in self.stages
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        """Сериализовать трассировку в словарь.

        Returns:
            Полный словарь трассировки для включения в JSON-ответ.
        """
        return {
            "request_id": self.request_id,
            "started_at": self.started_at,
            "elapsed_s": round(self.elapsed(), 4),
            "stages": [
                {
                    "name": s.name,
                    "duration_s": round(s.duration_s, 4),
                    "details": s.details,
                    "timestamp": s.timestamp,
                }
                for s in self.stages
            ],
            "metadata": self.metadata,
        }

    def elapsed(self) -> float:
        """Общее время с начала запроса.

        Returns:
            Время в секундах с момента создания контекста.
        """
        return time.monotonic() - self.started_at


def generate_request_id() -> str:
    """Сгенерировать уникальный идентификатор запроса.

    Returns:
        Hex-строка длиной 32 символа (uuid4).
    """
    return uuid.uuid4().hex


def format_log_record(record: dict[str, Any]) -> str:
    """Сериализовать запись лога в JSON-строку.

    Args:
        record: словарь с данными лога.

    Returns:
        JSON-строка, пригодная для stdout/файлового логгера.
    """
    return json.dumps(record, ensure_ascii=False, default=str)


def get_default_trace_context(request_id: str | None = None) -> RequestTraceContext:
    """Создать контекст трассировки с автоматическим request_id.

    Args:
        request_id: если не передан — генерируется автоматически.

    Returns:
        Новый экземпляр RequestTraceContext.
    """
    rid = request_id if request_id else generate_request_id()
    return RequestTraceContext(request_id=rid)


def is_json_serializable(value: Any) -> bool:
    """Проверить, что значение сериализуемо в JSON стандартными типами.

    Args:
        value: проверяемое значение.

    Returns:
        True если значение можно сериализовать через json.dumps без default.
    """
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False
