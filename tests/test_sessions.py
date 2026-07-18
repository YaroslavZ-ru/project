"""tests/test_sessions.py -- тесты SessionManager.

Не требуют внешних зависимостей. Config мокируется простым объектом.
"""

from pathlib import Path
import sys
import time
from types import SimpleNamespace

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.sessions import SessionManager  # noqa: E402


def make_config(
    ttl: int = 3600,
    maxsize: int = 10,
    interval: int = 3600,
):
    """Фабрика мок-конфига для SessionManager."""
    return SimpleNamespace(
        session_ttl_seconds=ttl,
        session_cache_size=maxsize,
        session_cleanup_interval_seconds=interval,
    )


class TestUpdateAndGet:
    def test_update_and_get_domain(self):
        """обновление и получение домена"""
        sm = SessionManager(make_config())
        sm.update_session("s1", "музыка", "ключ")
        assert sm.get_domain("s1") == "музыка"
        assert sm.session_count() == 1

    def test_update_overwrites_domain(self):
        """повторный вызов перезаписывает домен"""
        sm = SessionManager(make_config())
        sm.update_session("s1", "техника")
        sm.update_session("s1", "музыка")
        assert sm.get_domain("s1") == "музыка"

    def test_get_nonexistent_returns_none(self):
        """несуществующая сессия -> None"""
        sm = SessionManager(make_config())
        assert sm.get_domain("nonexistent") is None


class TestTTL:
    def test_expired_session_returns_none(self):
        """истекшая сессия возвращает None"""
        sm = SessionManager(make_config(ttl=0))
        sm.update_session("s2", "техника")
        time.sleep(0.01)
        assert sm.get_domain("s2") is None

    def test_cleanup_removes_expired(self):
        """публичный cleanup удаляет устаревшие сессии"""
        # interval=3600: автоочистка не срабатывает при update_session
        sm = SessionManager(make_config(ttl=0, interval=3600))
        sm.update_session("s1", "a")
        sm.update_session("s2", "b")
        time.sleep(0.01)
        removed = sm.cleanup()
        assert removed >= 2
        assert sm.session_count() == 0


class TestEviction:
    def test_max_size_eviction(self):
        """превышение maxsize вытесняет старейшуюс сессию"""
        sm = SessionManager(make_config(maxsize=2))
        sm.update_session("s1", "a")
        sm.update_session("s2", "b")
        sm.update_session("s3", "c")
        assert sm.session_count() <= 2


class TestEdgeCases:
    def test_none_session_id_ignored(self):
        """пустой/None session_id игнорируется"""
        sm = SessionManager(make_config())
        sm.update_session(None, "музыка")
        sm.update_session("", "техника")
        assert sm.session_count() == 0

    def test_get_returns_none_for_empty_id(self):
        """пустой session_id -> None"""
        sm = SessionManager(make_config())
        assert sm.get_domain("") is None
        assert sm.get_domain(None) is None


# --- Изменение 62: Тесты SQLite сессий ---


def make_sqlite_config(db_path, ttl=3600, maxsize=10, interval=3600):
    """Фабрика мок-конфига для SQLite SessionManager."""
    return SimpleNamespace(
        session_ttl_seconds=ttl,
        session_cache_size=maxsize,
        session_cleanup_interval_seconds=interval,
        session_storage="sqlite",
        db_path=str(db_path),
    )


class TestSQLiteSessions:
    def test_sqlite_create_and_get(self, tmp_path):
        """SQLite: создание и получение сессии."""
        db = tmp_path / "test.db"
        sm = SessionManager(make_sqlite_config(db))
        sm.update_session("s1", "музыка", "ключ")
        assert sm.get_domain("s1") == "музыка"
        assert sm.session_count() == 1

    def test_sqlite_update_domain(self, tmp_path):
        """SQLite: обновление домена."""
        db = tmp_path / "test.db"
        sm = SessionManager(make_sqlite_config(db))
        sm.update_session("s1", "техника")
        sm.update_session("s1", "музыка")
        assert sm.get_domain("s1") == "музыка"

    def test_sqlite_get_nonexistent(self, tmp_path):
        """SQLite: несуществующая сессия -> None."""
        db = tmp_path / "test.db"
        sm = SessionManager(make_sqlite_config(db))
        assert sm.get_domain("nonexistent") is None

    def test_sqlite_persistence(self, tmp_path):
        """SQLite: сессия переживает пересоздание SessionManager."""
        db = tmp_path / "test.db"
        sm1 = SessionManager(make_sqlite_config(db))
        sm1.update_session("s1", "музыка")
        # Создаём новый менеджер с тем же файлом
        sm2 = SessionManager(make_sqlite_config(db))
        assert sm2.get_domain("s1") == "музыка"

    def test_sqlite_cleanup(self, tmp_path):
        """SQLite: cleanup удаляет устаревшие сессии."""
        db = tmp_path / "test.db"
        sm = SessionManager(make_sqlite_config(db, ttl=0))
        sm.update_session("s1", "a")
        sm.update_session("s2", "b")
        time.sleep(0.01)
        removed = sm.cleanup()
        assert removed >= 2

    def test_sqlite_empty_session_id(self, tmp_path):
        """SQLite: пустой session_id игнорируется."""
        db = tmp_path / "test.db"
        sm = SessionManager(make_sqlite_config(db))
        sm.update_session("", "музыка")
        sm.update_session(None, "техника")
        assert sm.session_count() == 0
