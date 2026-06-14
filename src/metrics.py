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
        self._use_metrics   = use_metrics
        self._prometheus_on = use_metrics and _PROMETHEUS_AVAILABLE

        if use_metrics and not _PROMETHEUS_AVAILABLE:
            logger.warning(
                "prometheus_client не установлен. Метрики -- только внутренние."
            )
        elif not use_metrics:
            logger.info(
                "MetricsCollector: use_metrics=False. Внутренние счётчики активны."
            )

        # Внутренние счётчики -- активны всегда
        self._counts: dict[str, int] = {
            "requests_total":    0,
            "requests_ok":       0,
            "requests_fallback": 0,
            "requests_error":    0,
            "cache_hits":        0,
            "cache_misses":      0,
        }
        self._total_duration: float = 0.0
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

    def record_request(self, duration_s: float, status: str) -> None:
        """Записать один обработанный запрос.

        Args:
            duration_s: время обработки в секундах (>= 0).
            status:     одно из "ok" | "fallback" | "error".
        """
        with self._lock:
            self._counts["requests_total"] += 1
            key = "requests_" + status
            self._counts[key] = self._counts.get(key, 0) + 1
            self._total_duration += max(0.0, duration_s)

        if self._prometheus_on:
            try:
                self._prom_requests_total.labels(status=status).inc()
                self._prom_duration.observe(duration_s)
            except Exception as exc:  # noqa: BLE001
                logger.error("Ошибка Prometheus record_request: %s", exc)

        logger.debug(
            "metrics.record_request: status=%s, duration=%.3fs", status, duration_s
        )

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

    def get_summary(self) -> dict:
        """Вернуть снапшот внутренних метрик.

        Returns:
            Словарь с ключами:
              requests_total, requests_ok, requests_fallback, requests_error,
              cache_hits, cache_misses, avg_duration_s, prometheus_active.
        """
        with self._lock:
            total = self._counts["requests_total"]
            avg_dur = (self._total_duration / total) if total > 0 else 0.0
            return {
                "requests_total":    total,
                "requests_ok":       self._counts["requests_ok"],
                "requests_fallback": self._counts["requests_fallback"],
                "requests_error":    self._counts["requests_error"],
                "cache_hits":        self._counts["cache_hits"],
                "cache_misses":      self._counts["cache_misses"],
                "avg_duration_s":    round(avg_dur, 4),
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
            return generate_latest().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка generate_latest: %s", exc)
            return None
