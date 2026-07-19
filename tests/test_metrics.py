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


# --- Изменение 68/70: Тесты новых метрик ---


def test_record_ambiguous():
    """Запись ambiguous-запроса увеличивает requests_ambiguous."""
    mc = MetricsCollector(use_metrics=False)
    mc.record_request(10.0, "ambiguous")
    s = mc.get_summary()
    assert s["requests_ambiguous"] == 1
    assert s["requests_total"] == 1


def test_ema_pipeline_ms():
    """EMA-усреднение avg_pipeline_ms работает корректно."""
    mc = MetricsCollector(use_metrics=False)
    mc.record_request(0.1, "ok", elapsed_ms=100.0)
    mc.record_request(0.2, "ok", elapsed_ms=200.0)
    s = mc.get_summary()
    # EMA: first = 100, second = 0.9*100 + 0.1*200 = 110
    assert s["avg_pipeline_ms"] == 110.0


def test_record_generative_call():
    """Запись вызова генеративного расширения."""
    mc = MetricsCollector(use_metrics=False)
    mc.record_generative_call()
    assert mc.get_summary()["generative_calls"] == 1


def test_record_generative_timeout():
    """Запись таймаута генеративного расширения."""
    mc = MetricsCollector(use_metrics=False)
    mc.record_generative_timeout()
    assert mc.get_summary()["generative_timeouts"] == 1


def test_record_fallback():
    """Запись активации fallback."""
    mc = MetricsCollector(use_metrics=False)
    mc.record_fallback_activation()
    assert mc.get_summary()["fallback_activations"] == 1


def test_record_search_cache():
    """Запись cache_hits_search и cache_misses_search."""
    mc = MetricsCollector(use_metrics=False)
    mc.record_search_cache_hit()
    mc.record_search_cache_hit()
    mc.record_search_cache_miss()
    s = mc.get_summary()
    assert s["cache_hits_search"] == 2
    assert s["cache_misses_search"] == 1


def test_new_counters_initial_zero():
    """Новые счётчики инициализируются нулями."""
    mc = MetricsCollector(use_metrics=False)
    s = mc.get_summary()
    assert s["requests_ambiguous"] == 0
    assert s["generative_calls"] == 0
    assert s["generative_timeouts"] == 0
    assert s["fallback_activations"] == 0
    assert s["cache_hits_search"] == 0
    assert s["cache_misses_search"] == 0
    assert s["avg_pipeline_ms"] == 0.0
