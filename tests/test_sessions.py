"""tests/test_sessions.py -- тесты SessionManager.

Не требуют внешних зависимостей. Config мокируется простым объектом.
"""

import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.sessions import SessionManager


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

