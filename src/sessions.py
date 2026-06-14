"""src/sessions.py -- менеджер пользовательских сессий AI-Terminator.

Хранит состояние между запросами одного пользователя:
-- последний определённый домент учитывается в следующем запросе
-- TTL-кэш, потокобезопасный, авто-очистка по времени и по размеру
"""

import logging
import threading
import time
from dataclasses import dataclass

from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class SessionEntry:
    """Oдна сессия пользователя.

    Attributes:
        session_id: уникальный идентификатор сессии.
        domain:     последний подтверждённый домен.
        last_term:  последний термин запроса.
        created_at: time.monotonic() при создании.
        updated_at: time.monotonic() при последнем обновлении.
    """

    session_id: str
    domain: str | None
    last_term: str | None
    created_at: float
    updated_at: float


class SessionManager:
    """Менеджер сессий с TTL-кэшом и авто-очисткой.

    Потокобезопасен: все изменения защищены threading.Lock.
    Авто-очистка запускается при каждом update_session по истечению
    session_cleanup_interval_seconds.

    Attributes:
        _ttl:      время жизни сессии в секундах.
        _maxsize:  максимальное количество сессий.
        _interval: интервал между авто-очистками (с).
        _sessions: словарь session_id -> SessionEntry.
        _lock:     блокировка для потокобезопасности.
    """

    def __init__(self, config: Config) -> None:
        """Args:
            config: конфигурация AI-Terminator.
        """
        self._ttl: int = config.session_ttl_seconds
        self._maxsize: int = config.session_cache_size
        self._interval: int = config.session_cleanup_interval_seconds
        self._sessions: dict[str, SessionEntry] = {}
        self._lock = threading.Lock()
        self._last_cleanup: float = time.monotonic()

    def get_session(self, session_id: str) -> SessionEntry | None:
        """Возвращает сессию по идентификатору или None, если не найдена/истекла.

        Args:
            session_id: идентификатор сессии.

        Returns:
            SessionEntry или None.
        """
        if not session_id:
            return None
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            if time.monotonic() - entry.updated_at > self._ttl:
                del self._sessions[session_id]
                logger.debug("Сессия истекла: %s", session_id)
                return None
            return entry

    def update_session(
        self,
        session_id: str,
        domain: str | None,
        term: str | None = None,
    ) -> None:
        """Создаёт или обновляет сессию.

        Если достигнут лимит _maxsize -- удаляет старейшую сессию.

        Args:
            session_id: идентификатор сессии (пустой/None игнорируется).
            domain:     домен для сохранения.
            term:       последний термин запроса.
        """
        if not session_id:
            logger.warning(
                "SessionManager.update_session: пустой session_id, игнорируем."
            )
            return

        with self._lock:
            self._maybe_cleanup_unsafe()

            now = time.monotonic()
            if session_id not in self._sessions:
                # Вытеснение старейшей сессии при превышении лимита
                if len(self._sessions) >= self._maxsize:
                    oldest_id = min(
                        self._sessions,
                        key=lambda sid: self._sessions[sid].updated_at,
                    )
                    del self._sessions[oldest_id]
                    logger.warning(
                        "SessionManager: лимит %d, удалена старейшая сессия",
                        self._maxsize,
                    )
                self._sessions[session_id] = SessionEntry(
                    session_id=session_id,
                    domain=domain,
                    last_term=term,
                    created_at=now,
                    updated_at=now,
                )
            else:
                entry = self._sessions[session_id]
                entry.domain = domain
                entry.last_term = term if term is not None else entry.last_term
                entry.updated_at = now

            logger.debug(
                "Сессия обновлена: %s, domain=%s", session_id, domain
            )

    def get_domain(self, session_id: str) -> str | None:
        """Возвращает домен для сессии или None.

        Args:
            session_id: идентификатор сессии.

        Returns:
            Строка домена или None.
        """
        entry = self.get_session(session_id)
        return entry.domain if entry is not None else None

    def cleanup(self) -> int:
        """Удаляет все устаревшие сессии (публичный метод для внешнего вызова).

        Returns:
            Количество удалённых сессий.
        """
        with self._lock:
            return self._cleanup_unsafe()

    def session_count(self) -> int:
        """Текущее количество активных сессий.

        Returns:
            Целое число.
        """
        # Чтение len() dict на CPython атомарно
        return len(self._sessions)

    def _cleanup_unsafe(self) -> int:
        """Удаляет устаревшие сессии. Вызывать внутри захваченного self._lock.

        Returns:
            Количество удалённых сессий.
        """
        now = time.monotonic()
        expired = [
            sid for sid, e in self._sessions.items()
            if now - e.updated_at > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info(
                "SessionManager: удалено %d устаревших сессий",
                len(expired),
            )
        self._last_cleanup = now
        return len(expired)

    def _maybe_cleanup_unsafe(self) -> None:
        """Запускает очистку, если прошёл interval. Вызывать внутри self._lock."""
        if time.monotonic() - self._last_cleanup >= self._interval:
            self._cleanup_unsafe()
