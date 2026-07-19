"""src/metrics.py -- сбор внутренних метрик + экспорт в Prometheus.

Модуль полностью опциональный:
- внутренние счётчики (дикт, lock) активны всегда
- prometheus_client используется только при use_metrics=True и наличии библиотеки
- при отсутствии prometheus_client или use_metrics=False модуль не падает
Не является синглтоном; создаётся один раз в _init_components.
"""

import logging
import threading

logger = logging.getLogger(__name__)

# Опциональная зависимость: prometheus_client
_PROMETHEUS_AVAILABLE = True
try:
    import prometheus_client  # noqa: F401
    from prometheus_client import Counter, Histogram, generate_latest
except ImportError:
    _PROMETHEUS_AVAILABLE = False


class MetricsCollector:
    """Сбор внутренних метрик и опциональный экспорт в Prometheus.

    Внутренные счётчики активны всегда, независимо от use_metrics.
    Prometheus-експорт включается только при use_metrics=True
    и наличии prometheus_client.

    Потокобезопасен: все операции защищены threading.Lock.

    Attributes:
        _use_metrics:   флаг включения метрик.
        _prometheus_on: флаг активности Prometheus.
        _counts:        внутренние счётчики.
        _total_duration:сумма времён всех запросов (с).
        _lock:          блокировка.
    """

    def __init__(self, use_metrics: bool = False) -> None:
        """Args:
        use_metrics: если True -- при наличии prometheus_client активирует экспорт.
        """
        self._use_metrics = use_metrics
        self._prometheus_on = use_metrics and _PROMETHEUS_AVAILABLE

        if use_metrics and not _PROMETHEUS_AVAILABLE:
            logger.warning("prometheus_client не установлен. Метрики -- только внутренние.")
        elif not use_metrics:
            logger.info("MetricsCollector: use_metrics=False. Внутренние счётчики активны.")

        # Внутренние счётчики -- активны всегда
        self._counts: dict[str, int] = {
            "requests_total": 0,
            "requests_ok": 0,
            "requests_fallback": 0,
            "requests_error": 0,
            "requests_ambiguous": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_hits_search": 0,
            "cache_misses_search": 0,
            "generative_calls": 0,
            "generative_timeouts": 0,
            "fallback_activations": 0,
        }
        self._total_duration: float = 0.0
        # --- Изменение 70: EMA-усреднение ---
        self._avg_pipeline_ms: float = 0.0
        self._ema_alpha: float = 0.1
        self._lock = threading.Lock()

        # Prometheus-метрики -- только при _prometheus_on
        if self._prometheus_on:
            try:
                self._prom_requests_total = Counter(
                    "ait_requests_total",
                    "\u0412сего запросов AI-Terminator",
                    ["status"],
                )
                self._prom_duration = Histogram(
                    "ait_request_duration_seconds",
                    "\u0412ремя обработки запроса",
                )
                self._prom_cache_hits = Counter(
                    "ait_cache_hits_total",
                    "\u041fопаданий в кэш векторов",
                )
                logger.info("MetricsCollector: Prometheus-метрики зарегистрированы.")
            except ValueError:
                # Метрики уже зарегистрированы (например, повторное создание в тестах)
                logger.warning(
                    "MetricsCollector: Prometheus-метрики уже зарегистрированы. "
                    "Prometheus отключён."
                )
                self._prometheus_on = False

    def record_request(self, duration_s: float, status: str, elapsed_ms: float | None = None) -> None:
        """Записать один обработанный запрос.

        Args:
            duration_s: время обработки в секундах (>= 0).
            status:     одно из "ok" | "fallback" | "error" | "ambiguous".
            elapsed_ms: время обработки в миллисекундах (для EMA). None = вычислить из duration_s.
        """
        if elapsed_ms is None:
            elapsed_ms = duration_s * 1000.0

        with self._lock:
            self._counts["requests_total"] += 1
            key = "requests_" + status
            self._counts[key] = self._counts.get(key, 0) + 1
            self._total_duration += max(0.0, duration_s)
            # EMA: первый запрос задаёт начальное значение напрямую
            if self._counts["requests_total"] == 1:
                self._avg_pipeline_ms = elapsed_ms
            else:
                self._avg_pipeline_ms = (
                    (1 - self._ema_alpha) * self._avg_pipeline_ms
                    + self._ema_alpha * elapsed_ms
                )

        if self._prometheus_on:
            try:
                self._prom_requests_total.labels(status=status).inc()
                self._prom_duration.observe(duration_s)
            except Exception as exc:  # noqa: BLE001
                logger.error("Ошибка Prometheus record_request: %s", exc)

        logger.debug("metrics.record_request: status=%s, duration=%.3fs", status, duration_s)

    def record_cache_hit(self) -> None:
        """Зафиксировать попадание в кэш векторов."""
        with self._lock:
            self._counts["cache_hits"] += 1
        if self._prometheus_on:
            try:
                self._prom_cache_hits.inc()
            except Exception as exc:  # noqa: BLE001
                logger.error("Ошибка Prometheus record_cache_hit: %s", exc)

    def record_cache_miss(self) -> None:
        """Зафиксировать промах кэша векторов."""
        with self._lock:
            self._counts["cache_misses"] += 1

    def record_search_cache_hit(self) -> None:
        """Зафиксировать попадание в кэш поиска."""
        with self._lock:
            self._counts["cache_hits_search"] += 1

    def record_search_cache_miss(self) -> None:
        """Зафиксировать промах кэша поиска."""
        with self._lock:
            self._counts["cache_misses_search"] += 1

    def record_generative_call(self) -> None:
        """Зафиксировать вызов генеративного расширения."""
        with self._lock:
            self._counts["generative_calls"] += 1

    def record_generative_timeout(self) -> None:
        """Зафиксировать таймаут генеративного расширения."""
        with self._lock:
            self._counts["generative_timeouts"] += 1

    def record_fallback_activation(self) -> None:
        """Зафиксировать активацию fallback-режима."""
        with self._lock:
            self._counts["fallback_activations"] += 1

    def get_summary(self) -> dict:
        """Вернуть снапшот внутренних метрик.

        Returns:
            Словарь с ключами:
              requests_total, requests_ok, requests_fallback, requests_error,
              requests_ambiguous, cache_hits, cache_misses,
              cache_hits_search, cache_misses_search,
              generative_calls, generative_timeouts, fallback_activations,
              avg_duration_s, avg_pipeline_ms, prometheus_active.
        """
        with self._lock:
            total = self._counts["requests_total"]
            avg_dur = (self._total_duration / total) if total > 0 else 0.0
            return {
                "requests_total": total,
                "requests_ok": self._counts["requests_ok"],
                "requests_fallback": self._counts["requests_fallback"],
                "requests_error": self._counts["requests_error"],
                "requests_ambiguous": self._counts.get("requests_ambiguous", 0),
                "cache_hits": self._counts["cache_hits"],
                "cache_misses": self._counts["cache_misses"],
                "cache_hits_search": self._counts.get("cache_hits_search", 0),
                "cache_misses_search": self._counts.get("cache_misses_search", 0),
                "generative_calls": self._counts.get("generative_calls", 0),
                "generative_timeouts": self._counts.get("generative_timeouts", 0),
                "fallback_activations": self._counts.get("fallback_activations", 0),
                "avg_duration_s": round(avg_dur, 4),
                "avg_pipeline_ms": round(self._avg_pipeline_ms, 2),
                "prometheus_active": self._prometheus_on,
            }

    def get_prometheus_text(self) -> str | None:
        """Вернуть метрики в Prometheus text format или None.

        Returns:
            Строка в формате Prometheus text exposition,
            None если Prometheus не активен.
        """
        if not self._prometheus_on:
            return None
        try:
            result: str = generate_latest().decode("utf-8")
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка generate_latest: %s", exc)
            return None
