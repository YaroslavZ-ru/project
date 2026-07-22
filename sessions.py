"""src/sessions.py -- менеджер пользовательских сессий AI-Terminator.

Хранит состояние между запросами одного пользователя:
-- последний определённый домен учитывается в следующем запросе
-- TTL-кэш, потокобезопасный, авто-очистка по времени и по размеру

Поддерживает два режима хранения (изм. 62):
-- "memory"  : in-memory dict (по умолчанию, обратная совместимость)
-- "sqlite"  : персистентное хранилище в SQLite (переживает перезапуски)
"""

from dataclasses import dataclass
import datetime
import json
import logging
import sqlite3
import threading
import time
import uuid

from src.config import Config

logger = logging.getLogger(__name__)

# Проверка истечения TTL
_session_storage_counter = 0


@dataclass
class SessionEntry:
    """Одна сессия пользователя.

    Attributes:
        session_id: уникальный идентификатор сессии.
        domain:     последний подтверждённый домен.
        last_term:  последний термин запроса.
        created_at: time.monotonic() при создании (memory) или ISO timestamp (sqlite).
        updated_at: time.monotonic() при последнем обновлении (memory) или ISO timestamp (sqlite).
    """

    session_id: str
    domain: str | None
    last_term: str | None
    created_at: float | str
    updated_at: float | str


class SessionManager:
    """Менеджер сессий с TTL-кэшом и авто-очисткой.

    Поддерживает in-memory и SQLite хранилище (изм. 62).

    Потокобезопасен: все изменения защищены threading.Lock.
    Авто-очистка запускается при каждом update_session по истечению
    session_cleanup_interval_seconds.
    """

    def __init__(self, config: Config) -> None:
        """Args:
        config: конфигурация AI-Terminator.
        """
        self._ttl: int = config.session_ttl_seconds
        self._storage: str = getattr(config, "session_storage", "memory")

        if self._storage == "sqlite":
            self._db_path = str(config.db_path)
            self._maxsize: int = getattr(config, "session_cache_size", 1000)
            self._interval: int = getattr(config, "session_cleanup_interval_seconds", 60)
            self._ensure_table()
            # --- Изменение 74: Запуск фоновой очистки ---
            self.start_cleanup_timer()
        else:
            self._maxsize: int = getattr(config, "session_cache_size", 1000)
            self._interval: int = getattr(config, "session_cleanup_interval_seconds", 60)
            self._sessions: dict[str, SessionEntry] = {}

        self._lock = threading.Lock()
        self._last_cleanup: float = time.monotonic()

    # ------------------------------------------------------------------
    # SQLite: создание таблицы
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """Создать таблицу sessions, если не существует."""
        if self._storage != "sqlite":
            return
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id           TEXT PRIMARY KEY,
                    term         TEXT,
                    domain       TEXT,
                    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at   DATETIME
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)"
            )
            conn.commit()
            logger.info("Таблица sessions готова (SQLite)")
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Получить соединение с SQLite."""
        return sqlite3.connect(self._db_path, check_same_thread=False)

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> SessionEntry | None:
        """Возвращает сессию по идентификатору или None, если не найдена/истекла.

        Args:
            session_id: идентификатор сессии.

        Returns:
            SessionEntry или None.
        """
        if not session_id:
            return None

        if self._storage == "sqlite":
            return self._get_session_sqlite(session_id)
        else:
            return self._get_session_memory(session_id)

    def update_session(
        self,
        session_id: str,
        domain: str | None,
        term: str | None = None,
    ) -> None:
        """Создаёт или обновляет сессию.

        Args:
            session_id: идентификатор сессии (пустой/None игнорируется).
            domain:     домен для сохранения.
            term:       последний термин запроса.
        """
        if not session_id:
            logger.warning("SessionManager.update_session: пустой session_id, игнорируем.")
            return

        if self._storage == "sqlite":
            self._update_session_sqlite(session_id, domain, term)
        else:
            # M-11: Термин в сессии неизменяем — не обновлять если отличается
            with self._lock:
                entry = self._sessions.get(session_id)
                if entry is not None and term is not None and term != entry.last_term:
                    logger.warning(
                        "Сессия %s: попытка сменить термин с %r на %r. "
                        "Создайте новую сессию.",
                        session_id, entry.last_term, term,
                    )
                    return
            self._update_session_memory(session_id, domain, term)

    # --- Изменение 78: Коллизия UUID сессий ---

    def create_session(self, term: str = "", domain: str | None = None) -> str:
        """Создать новую сессию с уникальным UUID.

        При SQLite-хранилище обрабатывает коллизию UUID (макс. 3 попытки).

        Args:
            term:   термин для сохранения.
            domain: домен для сохранения.

        Returns:
            Уникальный session_id.
        """
        max_attempts = 3
        for attempt in range(max_attempts):
            session_id = str(uuid.uuid4())
            try:
                if self._storage == "sqlite":
                    conn = self._get_conn()
                    try:
                        now = datetime.datetime.now(datetime.timezone.utc)
                        expires = now + datetime.timedelta(seconds=self._ttl)
                        conn.execute(
                            "INSERT INTO sessions (id, term, domain, created_at, updated_at, expires_at) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (session_id, term, domain, now.isoformat(), now.isoformat(), expires.isoformat()),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                else:
                    self._update_session_memory(session_id, domain, term)
                logger.debug("Сессия создана: %s", session_id)
                return session_id
            except sqlite3.IntegrityError:
                if attempt < max_attempts - 1:
                    logger.warning(
                        "UUID коллизия, попытка %d/%d",
                        attempt + 1, max_attempts,
                    )
                    continue
                raise RuntimeError(
                    f"Не удалось создать сессию после {max_attempts} попыток"
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
            if self._storage == "sqlite":
                return self._cleanup_sqlite()
            else:
                return self._cleanup_unsafe()

    # --- Изменение 74: Очистка сессий и проверка TTL ---

    def cleanup_expired(self) -> int:
        """Удалить устаревшие сессии для обоих режимов хранения.

        Returns:
            Количество удалённых сессий.
        """
        if self._storage == "sqlite":
            conn = self._get_conn()
            try:
                now = datetime.datetime.now(datetime.timezone.utc)
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE expires_at <= ?",
                    (now.isoformat(),),
                )
                conn.commit()
                count = cursor.rowcount
                if count > 0:
                    logger.info("Session cleanup: удалено %d сессий", count)
                return count
            finally:
                conn.close()
        else:
            with self._lock:
                return self._cleanup_unsafe()

    def start_cleanup_timer(self) -> None:
        """Запустить фоновый поток периодической очистки сессий.

        Вызывается в __init__ для SQLite-хранилища.
        """
        def _cleanup_loop():
            while True:
                time.sleep(self._interval)
                try:
                    n = self.cleanup_expired()
                    if n > 0:
                        logger.info("Session cleanup: удалено %d сессий", n)
                except Exception as exc:
                    logger.error("Session cleanup error: %s", exc)

        t = threading.Thread(target=_cleanup_loop, daemon=True)
        t.start()
        logger.info("Session cleanup timer запущен (interval=%ds)", self._interval)

    def session_count(self) -> int:
        """Текущее количество активных сессий.

        Returns:
            Целое число.
        """
        if self._storage == "sqlite":
            return self._session_count_sqlite()
        return len(self._sessions)

    # ------------------------------------------------------------------
    # In-memory реализация
    # ------------------------------------------------------------------

    def _get_session_memory(self, session_id: str) -> SessionEntry | None:
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            now = time.monotonic()
            if now - entry.updated_at > self._ttl:
                del self._sessions[session_id]
                logger.debug("Сессия истекла: %s", session_id)
                return None
            return entry

    def _update_session_memory(
        self, session_id: str, domain: str | None, term: str | None
    ) -> None:
        with self._lock:
            self._maybe_cleanup_unsafe()
            now = time.monotonic()
            if session_id not in self._sessions:
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

            logger.debug("Сессия обновлена: %s, domain=%s", session_id, domain)

    def _cleanup_unsafe(self) -> int:
        now = time.monotonic()
        expired = [
            sid
            for sid, e in self._sessions.items()
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
        if time.monotonic() - self._last_cleanup >= self._interval:
            self._cleanup_unsafe()

    # ------------------------------------------------------------------
    # SQLite реализация (изм. 62)
    # ------------------------------------------------------------------

    def _get_session_sqlite(self, session_id: str) -> SessionEntry | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, term, domain, created_at, updated_at, expires_at "
                "FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            expires_at = row[5]
            if expires_at:
                exp = datetime.datetime.fromisoformat(expires_at)
                now = datetime.datetime.now(datetime.timezone.utc)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=datetime.timezone.utc)
                if now > exp:
                    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                    conn.commit()
                    logger.debug("Сессия истекла (SQLite): %s", session_id)
                    return None
            return SessionEntry(
                session_id=row[0],
                last_term=row[1],
                domain=row[2],
                created_at=row[3] or "",
                updated_at=row[4] or "",
            )
        finally:
            conn.close()

    def _update_session_sqlite(
        self, session_id: str, domain: str | None, term: str | None
    ) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = now + datetime.timedelta(seconds=self._ttl)
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO sessions (id, term, domain, created_at, updated_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, term, domain, now.isoformat(), now.isoformat(), expires.isoformat()),
                )
            else:
                updates = []
                params: list = []
                if domain is not None:
                    updates.append("domain = ?")
                    params.append(domain)
                if term is not None:
                    updates.append("term = ?")
                    params.append(term)
                if updates:
                    updates.append("updated_at = ?")
                    params.append(now.isoformat())
                    updates.append("expires_at = ?")
                    params.append(expires.isoformat())
                    params.append(session_id)
                    conn.execute(
                        f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
                        params,
                    )
            conn.commit()
            logger.debug("Сессия обновлена (SQLite): %s, domain=%s", session_id, domain)
        finally:
            conn.close()

    def _cleanup_sqlite(self) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE expires_at <= ?",
                (now.isoformat(),),
            )
            conn.commit()
            count = cursor.rowcount
            if count:
                logger.info("SessionManager (SQLite): удалено %d устаревших сессий", count)
            self._last_cleanup = time.monotonic()
            return count
        finally:
            conn.close()

    def _session_count_sqlite(self) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
