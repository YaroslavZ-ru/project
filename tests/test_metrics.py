"""tests/test_metrics.py -- unit-тесты MetricsCollector.

Не требует установки prometheus_client.
"""

import threading

from src.metrics import MetricsCollector


def test_initial_state_zero():
    """По умолчанию все счётчики нулевые, avg_duration_s = 0.0."""
    mc = MetricsCollector(use_metrics=False)
    summary = mc.get_summary()
    assert summary["requests_total"] == 0
    assert summary["requests_ok"] == 0
    assert summary["requests_fallback"] == 0
    assert summary["requests_error"] == 0
    assert summary["cache_hits"] == 0
    assert summary["cache_misses"] == 0
    assert summary["avg_duration_s"] == 0.0
    assert summary["prometheus_active"] is False


def test_record_request_ok():
    """Запись одного успешного запроса увеличивает нужные счётчики."""
    mc = MetricsCollector()
    mc.record_request(0.1, "ok")
    s = mc.get_summary()
    assert s["requests_total"] == 1
    assert s["requests_ok"] == 1
    assert s["requests_fallback"] == 0
    assert s["requests_error"] == 0
    assert s["avg_duration_s"] > 0.0


def test_record_multiple_requests():
    """Несколько запросов разных типов -- счётчики накапливаются корректно."""
    mc = MetricsCollector()
    mc.record_request(0.1, "ok")
    mc.record_request(0.2, "fallback")
    mc.record_request(0.3, "error")
    s = mc.get_summary()
    assert s["requests_total"] == 3
    assert s["requests_ok"] == 1
    assert s["requests_fallback"] == 1
    assert s["requests_error"] == 1
    assert abs(s["avg_duration_s"] - 0.2) < 0.001


def test_cache_hit_miss():
    """Попадания и промахи кэша считаются независимо."""
    mc = MetricsCollector()
    mc.record_cache_hit()
    mc.record_cache_hit()
    mc.record_cache_miss()
    s = mc.get_summary()
    assert s["cache_hits"] == 2
    assert s["cache_misses"] == 1


def test_get_prometheus_text_none_when_unavailable():
    """При use_metrics=False get_prometheus_text() возвращает None."""
    mc = MetricsCollector(use_metrics=False)
    assert mc.get_prometheus_text() is None


def test_thread_safety():
    """Согласованные записи из нескольких потоков -- нет гонок."""
    mc = MetricsCollector()

    def worker():
        for _ in range(100):
            mc.record_request(0.01, "ok")

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert mc.get_summary()["requests_total"] == 500
