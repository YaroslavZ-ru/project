"""src/api.py -- FastAPI REST API для AI-Terminator.

Опциональная зависимость: fastapi, pydantic (pip install fastapi uvicorn).
Запуск: python -m scripts.run_api

Компоненты инициализируются один раз при старте (lifespan context manager).
При отсутствии fastapi -- app = None, ImportError при попытке запустить.
"""

import asyncio
from collections import deque
import logging
from pathlib import Path
import secrets
import time

import numpy as np

from src.aggregation import aggregate_parameters, determine_context
from src.cache import QueryVectorCache
from src.config import Config
from src.embeddings import FastTextWrapper
from src.fallback import fallback_response
from src.generative import GenerativeExpander
from src.knowledge_base import KnowledgeBase
from src.lemmatizer import Lemmatizer
from src.metrics import MetricsCollector
from src.preprocess import preprocess
from src.sessions import SessionManager
from src.synonyms import SynonymDict
from src.vectorize import vectorize

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Опциональная зависимость: FastAPI
# ---------------------------------------------------------------------------

_FASTAPI_AVAILABLE = True
try:
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, PlainTextResponse
    from pydantic import BaseModel, ConfigDict, Field
except ImportError:
    _FASTAPI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Глобальное состояние приложения
# ---------------------------------------------------------------------------

_cfg: Config | None = None
_lemmatizer = None
_synonym_dict = None
_embedding_model = None
_vector_cache = None
_kb = None
_generative_expander = None
_session_manager = None
_metrics: MetricsCollector | None = None
_rate_store: dict[str, deque] = {}  # IP -> deque временных меток


# ---------------------------------------------------------------------------
# Pydantic-схемы (только при наличии FastAPI)
# ---------------------------------------------------------------------------

if _FASTAPI_AVAILABLE:

    class QueryRequest(BaseModel):
        """Схема входящего запроса к API."""

        term: str = Field(..., min_length=1, max_length=200, description="Термин для анализа")
        hints: list[str] = Field(default_factory=list, description="Уточняющие слова (до 3)")
        session_id: str | None = Field(None, description="ID сессии (опционально)")
        debug: bool = Field(False, description="Включить debug_info в ответ")
        min_confidence: float | None = Field(None, ge=0.0, le=1.0, description="Порог уверенности")

    class ParameterModel(BaseModel):
        name: str
        label_ru: str
        type: str
        description: str | None = None
        unit: str | None = None
        enum_values: list[str] | None = None
        confidence: float = 1.0

    class SelectedContext(BaseModel):
        domain: str | None = None
        concept_id: str | None = None
        term: str | None = None
        similarity: float | None = None

    class QueryResponse(BaseModel):
        model_config = ConfigDict(extra="ignore")
        status: str
        term: str = ""
        selected_context: SelectedContext = SelectedContext()
        needs_clarification: bool = False
        parameters: list[ParameterModel] = []
        suggested_refinements: list[str] = []
        warnings: list[str] = []
        debug_info: dict | None = None

    class HealthResponse(BaseModel):
        status: str
        version: str
        model_loaded: bool = False
        db_available: bool = False

    class KBStatsResponse(BaseModel):
        concepts_count: int
        parameters_count: int
        db_path: str


# ---------------------------------------------------------------------------
# Инициализация компонентов (дублирует _init_components из main.py)
# ---------------------------------------------------------------------------


def _api_init_components(cfg: Config) -> tuple:
    """Создать все ML-компоненты для API.

    Дублирует логику _init_components из main.py. ML-компоненты создаются
    ОДИН РАЗ при старте приложения через lifespan.

    Args:
        cfg: конфигурация приложения.

    Returns:
        Кортеж из 7 компонентов:
        (synonym_dict, lemmatizer, embedding_model, vector_cache,
         kb, generative_expander, session_manager).
    """
    lemmatizer = Lemmatizer(cache_size=cfg.cache_lemma_size)
    synonym_dict = SynonymDict(json_path=cfg.synonyms_path)
    fallback_path = cfg.fallback_embeddings_path if cfg.fallback_embeddings_path else None
    embedding_model = FastTextWrapper(
        model_path=cfg.fasttext_model_path,
        fallback_path=fallback_path,
        cache_size=cfg.word_vector_cache_size,
    )
    vector_cache = QueryVectorCache(maxsize=cfg.query_cache_size)
    kb = KnowledgeBase(config=cfg, embedding_model=embedding_model, synonym_dict=synonym_dict)
    generative_expander = GenerativeExpander(config=cfg)
    session_manager = SessionManager(config=cfg)
    return (
        synonym_dict,
        lemmatizer,
        embedding_model,
        vector_cache,
        kb,
        generative_expander,
        session_manager,
    )


# ---------------------------------------------------------------------------
# Пайплайн для API (с записью метрик)
# ---------------------------------------------------------------------------


def _api_run_pipeline(
    term: str,
    hints: list[str],
    debug: bool,
    min_confidence: float | None,
    cfg: Config,
    lemmatizer,
    synonym_dict,
    embedding_model,
    vector_cache,
    kb,
    generative_expander,
    session_manager,
    session_id: str | None,
    metrics: MetricsCollector | None,
) -> dict:
    """Запустить пайплайн и зафиксировать метрики.

    Args:
        term:               очищенный термин.
        hints:              уточняющие подсказки (до 3).
        debug:              флаг отладки.
        min_confidence:     порог уверенности (None = из конфига).
        cfg:                конфигурация.
        lemmatizer:         лемматизатор.
        synonym_dict:       словарь синонимов.
        embedding_model:    FastTextWrapper.
        vector_cache:       кэш векторов запросов.
        kb:                 база знаний.
        generative_expander: генеративный расширитель.
        session_manager:    менеджер сессий.
        session_id:         ID сессии или None.
        metrics:            коллектор метрик или None.

    Returns:
        Словарь результата пайплайна.
    """
    start = time.monotonic()
    result: dict = {"status": "error", "message": "Неизвестная ошибка"}

    try:
        if hints is None:
            hints = []

        effective_min_confidence = (
            min_confidence if min_confidence is not None else cfg.min_confidence
        )

        # Шаг 1: предобработка
        processed = preprocess(term, hints, cfg, synonym_dict, lemmatizer)
        if processed["status"] == "error":
            result = {"status": "error", "message": processed["message"]}
            return result

        warnings_list = list(processed.get("warnings", []))

        # Шаг 2: векторизация с кэшем
        query_vector = None
        if vector_cache is not None:
            query_vector = vector_cache.get(term, hints, cfg)
            if query_vector is not None and metrics:
                metrics.record_cache_hit()

        if query_vector is None:
            if metrics:
                metrics.record_cache_miss()
            query_vector = vectorize(processed, embedding_model)
            if vector_cache is not None:
                vector_cache.put(term, hints, cfg, query_vector)

        if np.all(query_vector == 0):
            warnings_list.append(
                "Вектор запроса нулевой. Модель эмбеддингов недоступна. Поиск не выполнен."
            )

        # Шаг 3: поиск кандидатов
        candidates: list = []
        if kb is not None and not np.all(query_vector == 0):
            candidates = kb.search_similar_concepts(
                query_vector,
                min_confidence=effective_min_confidence,
                max_candidates=cfg.max_candidates,
            )
        elif kb is None:
            warnings_list.append("KnowledgeBase не инициализирован. Поиск пропущен.")

        # Шаг 4: агрегация или fallback
        if candidates:
            hints_lemmas = processed.get("hints_lemmas", [])
            parameters = aggregate_parameters(candidates, hints_lemmas, cfg.max_parameters)
            selected_context = determine_context(candidates)
            suggested_refinements: list = []

            if (
                cfg.use_generative
                and generative_expander is not None
                and len(parameters) < cfg.min_parameters_for_generative
            ):
                gen_params = generative_expander.expand(term, hints, parameters, cfg)
                if gen_params:
                    parameters.extend(gen_params)
                    warnings_list.append(
                        f"Добавлено {len(gen_params)} параметров генеративной моделью."
                    )

            if len(parameters) < 3:
                warnings_list.append("Найдено мало параметров. Рекомендуется уточнить запрос.")

            result = {
                "status": "ok",
                "term": term,
                "selected_context": selected_context,
                "parameters": parameters,
                "suggested_refinements": suggested_refinements,
                "warnings": warnings_list,
            }
        else:
            result = fallback_response(term, processed, cfg)

        if debug and "debug_info" not in result:
            result["debug_info"] = {
                "query_vector": query_vector.tolist(),
                "candidates_raw": candidates,
            }

        # Сессия
        if session_manager and session_id:
            domain = None
            sc = result.get("selected_context")
            if isinstance(sc, dict):
                domain = sc.get("domain")
            if (
                result.get("status") == "ok"
                and cfg.auto_save_domain_on_ok
                and domain
                or (result.get("status") == "ok" and cfg.auto_save_domain_on_fallback and domain)
            ):
                session_manager.update_session(session_id, domain, term)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка в пайплайне API: %s", exc)
        result = {"status": "error", "message": f"Внутренняя ошибка: {exc}"}

    finally:
        duration = time.monotonic() - start
        status = result.get("status", "error")
        if metrics:
            metrics.record_request(duration, status)

    return result


# ---------------------------------------------------------------------------
# FastAPI приложение
# ---------------------------------------------------------------------------


def _configure_api_logging(log_level: str, project_root) -> None:
    """Настроить логирование API: StreamHandler + RotatingFileHandler.

    Args:
        log_level:    уровень логирования.
        project_root: корень проекта.
    """
    import logging
    from logging.handlers import RotatingFileHandler
    from pathlib import Path
    import sys

    FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter(FORMAT))
    root_logger.addHandler(sh)
    logs_dir = Path(project_root) / "logs"
    if logs_dir.exists():
        try:
            fh = RotatingFileHandler(
                str(logs_dir / "api.log"),
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            fh.setFormatter(logging.Formatter(FORMAT))
            root_logger.addHandler(fh)
        except (OSError, PermissionError):
            pass


if not _FASTAPI_AVAILABLE:
    logger.warning(
        "fastapi не установлен. Модуль src.api загружен, но app недоступен. "
        "Установите: pip install fastapi uvicorn"
    )
    app = None  # type: ignore[assignment]

else:
    pass  # FastAPI доступен

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan: инициализация при старте, очистка при завершении."""
        global _cfg, _lemmatizer, _synonym_dict, _embedding_model
        global _vector_cache, _kb, _generative_expander, _session_manager, _metrics

        # --- Startup ---
        PROJECT_ROOT = Path(__file__).parent.parent
        _configure_api_logging(
            getattr(_cfg, "log_level", "INFO") if _cfg else "INFO",
            PROJECT_ROOT,
        )
        try:
            _cfg = Config.from_json("configs/config.json", project_root=PROJECT_ROOT)
            logger.info("API: конфигурация загружена")
        except Exception as exc:
            logger.error("API: ошибка загрузки конфига: %s", exc)
            yield
            return

        try:
            (
                _synonym_dict,
                _lemmatizer,
                _embedding_model,
                _vector_cache,
                _kb,
                _generative_expander,
                _session_manager,
            ) = _api_init_components(_cfg)
            logger.info("API: все компоненты инициализированы")
        except Exception as exc:
            logger.error("API: ошибка инициализации компонентов: %s", exc)
            yield
            return

        _metrics = MetricsCollector(use_metrics=_cfg.use_metrics)
        logger.info("API: MetricsCollector создан")

        # Прогрев модели
        try:
            _ = _embedding_model.get_word_vector("а")
            logger.info("API: прогрев FastText завершён")
        except Exception as exc:
            logger.warning("API: прогрев завершился с ошибкой: %s", exc)

        yield  # Приложение работает

        # --- Shutdown ---
        if _kb:
            try:
                _kb.close()
                logger.info("API: KnowledgeBase закрыт")
            except Exception as exc:
                logger.warning("API: ошибка при закрытии KnowledgeBase: %s", exc)

    # ------ вспомогательные функции защиты ------
    def _check_rate_limit(ip: str, rpm: int) -> bool:
        """True → запрос разрешён. False → превышен лимит."""
        now = time.monotonic()
        q = _rate_store.setdefault(ip, deque())
        while q and now - q[0] > 60.0:
            q.popleft()
        if len(q) >= rpm:
            return False
        q.append(now)
        return True

    def _verify_api_key(request: Request) -> None:
        if _cfg is None or _cfg.api_key_enabled is not True:
            return
        key = request.headers.get("X-API-Key", "")
        if not key:
            raise HTTPException(401, detail="Требуется заголовок X-API-Key")
        if not secrets.compare_digest(key, _cfg.api_key):
            logger.warning("Неверный API key IP=%s", request.client.host if request.client else "?")
            raise HTTPException(403, detail="Неверный API key")

    app = FastAPI(
        title="AI-Terminator API",
        description="REST API для интеллектуального анализа терминов",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    @app.post("/v1/query", response_model=QueryResponse)
    async def query(request: Request, body: QueryRequest) -> QueryResponse:
        """Обработать запрос: термин + подсказки -> список параметров."""
        _verify_api_key(request)
        if _cfg is None:
            raise HTTPException(503, detail="Сервис запускается. Попробуйте позже.")
        _rpm = getattr(_cfg, "rate_limit_rpm", 0)
        if isinstance(_rpm, int) and _rpm > 0:
            ip = request.client.host if request.client else "unknown"
            if not _check_rate_limit(ip, _cfg.rate_limit_rpm):
                raise HTTPException(429, detail="Слишком много запросов. Попробуйте позже.")
        hints = [h.strip() for h in body.hints if h.strip()][:3]
        try:
            result = await asyncio.to_thread(
                _api_run_pipeline,
                body.term,
                hints,
                body.debug,
                body.min_confidence,
                _cfg,
                _lemmatizer,
                _synonym_dict,
                _embedding_model,
                _vector_cache,
                _kb,
                _generative_expander,
                _session_manager,
                body.session_id,
                _metrics,
            )
        except ValueError as exc:
            raise HTTPException(400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Необработанная ошибка в /v1/query: %s", exc)
            raise HTTPException(500, detail="Внутренняя ошибка сервера") from None
        return QueryResponse.model_validate(result)

    @app.post("/query", response_model=QueryResponse, include_in_schema=False)
    async def query_legacy(request: Request, body: QueryRequest) -> QueryResponse:
        return await query(request, body)

    @app.get("/v1/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Проверка готовности сервиса."""
        if _cfg is None:
            return HealthResponse(status="starting", version="1.0.0")

        model_loaded = bool(_embedding_model is not None and _embedding_model._model_loaded)
        db_available = bool(_kb is not None and _kb._conn)

        return HealthResponse(
            status="ok", version="1.0.0", model_loaded=model_loaded, db_available=db_available
        )

    @app.get("/health", response_model=HealthResponse, include_in_schema=False)
    async def health_legacy() -> HealthResponse:
        return await health()

    @app.get("/v1/metrics", include_in_schema=False)
    async def metrics_endpoint():
        """Метрики сервиса в формате Prometheus text или JSON."""
        if _metrics is None:
            return JSONResponse({"error": "metrics not initialized"})

        prometheus_text = _metrics.get_prometheus_text()
        if prometheus_text is not None:
            return PlainTextResponse(
                prometheus_text,
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
        return JSONResponse(_metrics.get_summary())

    @app.get("/metrics", include_in_schema=False)
    async def metrics_legacy():
        return await metrics_endpoint()

    @app.get("/v1/kb/stats", response_model=KBStatsResponse)
    async def kb_stats():
        """Статистика базы знаний: количество концептов и параметров."""
        if _kb is None:
            raise HTTPException(503, detail="KB не инициализирован")

        try:
            concepts = _kb.get_all_concepts(use_cache=True)
            total_params = sum(len(c["parameters"]) for c in concepts)
            return JSONResponse(
                {
                    "concepts_count": len(concepts),
                    "parameters_count": total_params,
                    "db_path": str(_kb._db_path),
                }
            )
        except Exception as exc:
            logger.error("Ошибка в /kb/stats: %s", exc)
            raise HTTPException(500, detail="Ошибка получения статистики БД") from exc
    @app.get("/kb/stats", include_in_schema=False)
    async def kb_stats_legacy():
        return await kb_stats()

