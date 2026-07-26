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

from src.aggregation import (
    aggregate_parameters,
    apply_feedback_correction,
    check_hints_coherence,
    determine_context,
    detect_ambiguity,
    generate_clarification_questions,
)
from src.cache import QueryVectorCache
from src.config import Config
from src.embeddings import FastTextWrapper
from src.fallback import fallback_response
from src.generative import GenerativeExpander
from src.knowledge_base import KnowledgeBase
from src.lemmatizer import Lemmatizer
from src.metrics import MetricsCollector
from src.observability import RequestTraceContext, generate_request_id, get_default_trace_context
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
    from typing import cast as _cast

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
        selected_domain: str | None = Field(None, description="Выбранный домен при неоднозначности")

    class ParameterModel(BaseModel):
        name: str
        label_ru: str
        type: str
        description: str | None = None
        unit: str | None = None
        enum_values: list[str] | None = None
        confidence: float = 1.0
        source: str = "knowledge_base"

    # --- Изменение 69: domain_candidates ---

    class DomainCandidate(BaseModel):
        domain: str
        confidence: float
        example_term: str | None = None

    class SelectedContext(BaseModel):
        model_config = ConfigDict(extra="ignore")
        domain: str | None = None
        confidence: float | None = None
        domain_candidates: list[DomainCandidate] | None = None

    class QueryResponse(BaseModel):
        model_config = ConfigDict(extra="ignore")
        status: str
        term: str = ""
        selected_context: SelectedContext = SelectedContext()
        parameters: list[ParameterModel] = []
        suggested_refinements: list[str] = []
        warnings: list[str] = []

    class HealthResponse(BaseModel):
        status: str
        version: str
        model_loaded: bool = False
        db_available: bool = False

    class KBStatsResponse(BaseModel):
        concepts_count: int
        parameters_count: int
        db_path: str

    # --- Изменение 61: Пакетная обработка ---

    class BatchQueryItem(BaseModel):
        term: str = Field(..., min_length=1, max_length=200)
        hints: list[str] = Field(default_factory=list)
        session_id: str | None = None
        selected_domain: str | None = None

    class BatchQueryRequest(BaseModel):
        requests: list[BatchQueryItem] = Field(..., min_length=1)
        debug: bool = False
        max_batch_size: int | None = None

    class BatchQueryResponse(BaseModel):
        results: list[QueryResponse]
        total: int
        successful: int
        failed: int

    # --- Изменение 66: Сохранение понятий ---

    class ConceptParameter(BaseModel):
        name: str = Field(..., min_length=1)
        label_ru: str = Field(..., min_length=1)
        type: str = Field(..., pattern=r"^(string|integer|float|boolean|enum)$")
        description: str | None = None
        unit: str | None = None
        enum_values: list[str] | None = None
        confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    class ConceptRelation(BaseModel):
        target_term: str = Field(..., min_length=1)
        relation_type: str = Field(..., pattern=r"^(is_a|part_of|related_to|synonym)$")
        confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    class SaveConceptRequest(BaseModel):
        term: str = Field(..., min_length=1, max_length=200)
        domain: str = Field(..., min_length=1)
        parameters: list[ConceptParameter] = Field(default_factory=list)
        relations: list[ConceptRelation] = Field(default_factory=list)

    class SaveConceptResponse(BaseModel):
        concept_id: str
        status: str = "ok"

    # --- Изменение 68: Обратная связь ---

    class FeedbackRequest(BaseModel):
        session_id: str | None = None
        concept_id: str | None = None
        term: str = Field(..., min_length=1)
        rating: int = Field(..., ge=1, le=5)
        comment: str | None = None


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
    request_id: str | None = None,
    trace_context: RequestTraceContext | None = None,
    selected_domain: str | None = None,
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
        request_id:         уникальный ID запроса для трассировки.
        trace_context:      контекст трассировки для фиксации этапов.

    Returns:
        Словарь результата пайплайна.
    """
    start = time.monotonic()
    result: dict = {"status": "error", "message": "Неизвестная ошибка"}

    # Создать контекст трассировки, если не передан
    if trace_context is None:
        trace_context = get_default_trace_context(request_id)
        request_id = trace_context.request_id

    try:
        if hints is None:
            hints = []

        effective_min_confidence = (
            min_confidence if min_confidence is not None else cfg.min_confidence
        )

        # Шаг 1: предобработка
        t_stage = time.monotonic()
        processed = preprocess(term, hints, cfg, synonym_dict, lemmatizer)
        trace_context.add_stage("preprocess", time.monotonic() - t_stage, {"lemmas": len(processed.get("all_lemmas", []))})
        if processed["status"] == "error":
            result = {"status": "error", "message": processed["message"]}
            return result

        warnings_list = list(processed.get("warnings", []))

        # Изменение 63: Проверка связности подсказок
        if hints and len(hints) >= 2 and _embedding_model is not None:
            coherence_threshold = getattr(_cfg, "hints_coherence_threshold", 0.2)
            coherence = check_hints_coherence(hints, _embedding_model, coherence_threshold)
            if not coherence["coherent"]:
                warnings_list.append(
                    f"Подсказки имеют низкую семантическую связность "
                    f"(сходство {coherence['avg_similarity']:.2f} < {coherence_threshold}). "
                    f"Результаты могут быть неточными."
                )
                logger.info("Несвязные подсказки: %s", coherence["reason"])

        # Шаг 2: векторизация с кэшем
        t_stage = time.monotonic()
        query_vector = None
        cache_hit = False
        if vector_cache is not None:
            query_vector = vector_cache.get(term, hints, cfg)
            if query_vector is not None:
                cache_hit = True
                if metrics:
                    metrics.record_cache_hit()

        if query_vector is None:
            if metrics:
                metrics.record_cache_miss()
            query_vector = vectorize(processed, embedding_model)
            if vector_cache is not None:
                vector_cache.put(term, hints, cfg, query_vector)
        trace_context.add_stage("vectorize", time.monotonic() - t_stage, {"cache_hit": cache_hit})

        if np.all(query_vector == 0):
            warnings_list.append(
                "Вектор запроса нулевой. Модель эмбеддингов недоступна. Поиск не выполнен."
            )

        # Шаг 3: поиск кандидатов
        t_stage = time.monotonic()
        candidates: list = []
        if kb is not None and not np.all(query_vector == 0):
            candidates = kb.search_similar_concepts(
                query_vector,
                min_confidence=effective_min_confidence,
                max_candidates=cfg.max_candidates,
                domain_filter=selected_domain,
            )
        elif kb is None:
            warnings_list.append("KnowledgeBase не инициализирован. Поиск пропущен.")
        trace_context.add_stage("search", time.monotonic() - t_stage, {"candidates_count": len(candidates)})

        # --- Фильтрация домена по hints ---
        if candidates and hints:
            hints_lemmas_flat = [lemma for sub in processed.get("hints_lemmas", []) for lemma in sub]
            if hints_lemmas_flat:
                from src.fallback import detect_domain
                hint_domain = detect_domain(set(hints_lemmas_flat), cfg.fallback_domain_keywords_path)
                if hint_domain and hint_domain != "general":
                    filtered = [c for c in candidates if c.get("domain") == hint_domain]
                    if filtered:
                        candidates = filtered

        # --- Проверка минимального confidence ---
        if candidates:
            best_sim = max(c.get("similarity", 0.0) for c in candidates)
            if best_sim < 0.3:
                candidates = []

        # --- Изменение 68: Коррекция по обратной связи ---
        if (
            getattr(cfg, "use_feedback_correction", False)
            and kb is not None
            and candidates
        ):
            candidates = apply_feedback_correction(
                candidates,
                kb,
                weight=getattr(cfg, "feedback_weight", 0.1),
                min_votes=getattr(cfg, "feedback_min_votes", 3),
            )

        # Шаг 4: агрегация или fallback
        t_stage = time.monotonic()
        if candidates:
            hints_lemmas = processed.get("hints_lemmas", [])

            # Определяем контекст ДО фильтрации (для ambiguity detection)
            selected_context = determine_context(candidates)

            # --- Блок A: Обнаружение неоднозначности ---
            ambiguity_info = detect_ambiguity(
                candidates,
                threshold=cfg.ambiguity_threshold,
                delta=cfg.ambiguity_delta,
            )
            needs_clarification: bool = ambiguity_info["is_ambiguous"]
            if needs_clarification:
                clarification_questions = generate_clarification_questions(ambiguity_info, term)
                suggested_refinements = clarification_questions
                warnings_list.append(
                    f"Термин неоднозначен: возможны домены "
                    f"'{ambiguity_info['top_domain']}' и '{ambiguity_info['runner_up']}'. "
                    f"Добавьте уточняющие подсказки."
                )
            else:
                # Неоднозначности нет — фильтруем кандидатов по домену
                primary_domain = selected_context.get("domain")
                if primary_domain and primary_domain != "не определено":
                    domain_filtered = [c for c in candidates if c.get("domain") == primary_domain]
                    if domain_filtered:
                        candidates = domain_filtered

            # --- Фильтр similarity: отбросить кандидатов < 70% от лучшего ---
            if candidates:
                top_sim = max(c.get("similarity", 0.0) for c in candidates)
                threshold_sim = top_sim * 0.7
                candidates = [c for c in candidates if c.get("similarity", 0.0) >= threshold_sim]

            # --- Изменение 67: Параметры из графа отношений ---
            related_params: list = []
            if getattr(cfg, "use_relations", False) and kb is not None:
                for candidate in candidates:
                    concept_id = candidate.get("concept_id")
                    if concept_id:
                        rp = kb.get_related_concept_params(
                            concept_id,
                            depth=getattr(cfg, "relation_max_depth", 1),
                        )
                        related_params.extend(rp)

            if related_params:
                parameters = aggregate_parameters(candidates, hints_lemmas, cfg.max_parameters, related_params=related_params)
            else:
                parameters = aggregate_parameters(candidates, hints_lemmas, cfg.max_parameters)

            # Генерация suggested_refinements
            suggested_refinements: list = []
            for p in parameters:
                if p.get("type") == "enum" and p.get("enum_values"):
                    label = p.get("label_ru", p.get("name", ""))
                    values = ", ".join(p["enum_values"][:6])
                    suggested_refinements.append(f"Уточните {label.lower()}: {values}")

            if (
                cfg.use_generative
                and generative_expander is not None
                and len(parameters) < cfg.min_parameters_for_generative
            ):
                if metrics:
                    metrics.record_generative_call()
                gen_params = generative_expander.expand(term, hints, parameters, cfg)
                if gen_params:
                    parameters.extend(gen_params)
                    warnings_list.append(
                        f"Добавлено {len(gen_params)} параметров генеративной моделью."
                    )

            if len(parameters) < 3:
                warnings_list.append("Найдено мало параметров. Рекомендуется уточнить запрос.")

            if needs_clarification:
                result = {
                    "status": "ambiguous",
                    "term": term,
                    "selected_context": {
                        "domain_candidates": ambiguity_info.get("domain_candidates", []),
                    },
                    "parameters": [],
                    "suggested_refinements": suggested_refinements,
                    "warnings": warnings_list,
                }
            else:
                result = {
                    "status": "ok",
                    "term": term,
                    "selected_context": selected_context,
                    "parameters": parameters,
                    "suggested_refinements": suggested_refinements,
                    "warnings": warnings_list,
                }
        else:
            if metrics:
                metrics.record_fallback_activation()
            result = fallback_response(term, processed, cfg)
        trace_context.add_stage("aggregation", time.monotonic() - t_stage, {"parameters_count": len(result.get("parameters", []))})

        if debug and "debug_info" not in result:
            result["debug_info"] = {
                "query_vector": query_vector.tolist(),
                "candidates_raw": candidates,
            }
            result["trace"] = trace_context.to_dict()

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
        result = {"status": "error", "message": f"Внутренняя ошибка: {exc}", "request_id": request_id}

    finally:
        duration = time.monotonic() - start
        status = result.get("status", "error")
        if metrics:
            metrics.record_request(duration, status)

    return result


# ---------------------------------------------------------------------------
# FastAPI приложение
# ---------------------------------------------------------------------------


def _configure_api_logging(log_level: str, project_root, log_format: str = "text") -> None:
    """Настроить логирование API: StreamHandler + RotatingFileHandler.

    Args:
        log_level:    уровень логирования.
        project_root: корень проекта.
        log_format:   формат логов "text" или "json" (изм. 65).
    """
    import logging
    from logging.handlers import RotatingFileHandler
    from pathlib import Path
    import sys

    from src.utils import JSONFormatter

    FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(FORMAT)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
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
            fh.setFormatter(formatter)
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
            getattr(_cfg, "log_format", "text") if _cfg else "text",
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
        # Получить или сгенерировать request_id
        request_id = request.headers.get("X-Request-Id") or generate_request_id()
        trace_context = get_default_trace_context(request_id)
        logger.info("request.start request_id=%s path=%s", request_id[:8], str(request.url))
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
                request_id,
                trace_context,
                body.selected_domain,
            )
        except ValueError as exc:
            raise HTTPException(400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Необработанная ошибка в /v1/query: %s", exc)
            raise HTTPException(500, detail="Внутренняя ошибка сервера") from None
        logger.info("request.complete request_id=%s status=%s", request_id[:8], result.get("status"))
        return _cast(QueryResponse, QueryResponse.model_validate(result))

    @app.post("/query", response_model=QueryResponse, include_in_schema=False)
    async def query_legacy(request: Request, body: QueryRequest) -> QueryResponse:
        return _cast(QueryResponse, await query(request, body))

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
        return _cast(HealthResponse, await health())

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

    # --- Изменение 61: Пакетная обработка ---

    @app.post("/v1/process_batch", response_model=BatchQueryResponse)
    async def process_batch(request: Request, body: BatchQueryRequest) -> BatchQueryResponse:
        """Обработать пакет запросов: несколько терминов за один HTTP-запрос."""
        _verify_api_key(request)
        if _cfg is None:
            raise HTTPException(503, detail="Сервис запускается. Попробуйте позже.")

        effective_limit = body.max_batch_size or _cfg.max_batch_size
        if len(body.requests) > effective_limit:
            raise HTTPException(
                400,
                detail=f"Пакет слишком большой: {len(body.requests)} > {effective_limit}",
            )

        results: list = []
        for item in body.requests:
            try:
                hints = [h.strip() for h in item.hints if h.strip()][:3]
                request_id = generate_request_id()
                trace_context = get_default_trace_context(request_id)
                result = await asyncio.to_thread(
                    _api_run_pipeline,
                    item.term,
                    hints,
                    body.debug,
                    None,
                    _cfg,
                    _lemmatizer,
                    _synonym_dict,
                    _embedding_model,
                    _vector_cache,
                    _kb,
                    _generative_expander,
                    _session_manager,
                    item.session_id,
                    _metrics,
                    request_id,
                    trace_context,
                )
                results.append(QueryResponse.model_validate(result))
            except Exception as exc:
                logger.error("Ошибка в batch для %r: %s", item.term, exc)
                results.append(QueryResponse(
                    status="error",
                    term=item.term,
                    warnings=[f"Ошибка обработки: {exc}"],
                ))

        successful = sum(1 for r in results if r.status == "ok")
        return BatchQueryResponse(
            results=results,
            total=len(results),
            successful=successful,
            failed=len(results) - successful,
        )

    @app.post("/process_batch", response_model=BatchQueryResponse, include_in_schema=False)
    async def process_batch_legacy(request: Request, body: BatchQueryRequest) -> BatchQueryResponse:
        return await process_batch(request, body)

    # --- Изменение 66: POST /v1/save_concept ---

    @app.post("/v1/save_concept", response_model=SaveConceptResponse)
    async def save_concept_endpoint(request: Request, body: SaveConceptRequest) -> SaveConceptResponse:
        """Сохранить новое понятие в базу знаний."""
        _verify_api_key(request)
        if _cfg is None or _kb is None:
            raise HTTPException(503, detail="Сервис не готов")

        try:
            parameters = [
                {
                    "name": p.name,
                    "label_ru": p.label_ru,
                    "type": p.type,
                    "description": p.description,
                    "unit": p.unit,
                    "enum_values": p.enum_values,
                    "confidence": p.confidence,
                }
                for p in body.parameters
            ]

            relations = [
                {
                    "target_term": r.target_term,
                    "relation_type": r.relation_type,
                    "confidence": r.confidence,
                }
                for r in body.relations
            ]

            concept_id = await asyncio.to_thread(
                _kb.save_concept,
                body.term,
                body.domain,
                parameters,
                relations if relations else None,
            )
            return SaveConceptResponse(concept_id=concept_id)
        except Exception as exc:
            logger.exception("Ошибка save_concept: %s", exc)
            raise HTTPException(500, detail=f"Ошибка сохранения: {exc}") from exc

    @app.post("/save_concept", response_model=SaveConceptResponse, include_in_schema=False)
    async def save_concept_legacy(request: Request, body: SaveConceptRequest) -> SaveConceptResponse:
        return await save_concept_endpoint(request, body)

    # --- Изменение 68: POST /v1/feedback ---

    @app.post("/v1/feedback")
    async def feedback_endpoint(request: Request, body: FeedbackRequest) -> dict:
        """Принять обратную связь по результату поиска (rating 1-5)."""
        _verify_api_key(request)
        if _cfg is None:
            raise HTTPException(503, detail="Сервис не готов")

        try:
            if _kb is not None:
                with _kb._db_lock:
                    _kb._conn.execute(
                        "INSERT INTO feedback (session_id, concept_id, term, rating, comment) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (body.session_id, body.concept_id, body.term, body.rating, body.comment),
                    )
                    _kb._conn.commit()
            else:
                import sqlite3 as _sqlite3

                conn = _sqlite3.connect(str(_cfg.db_path))
                try:
                    conn.execute(
                        "INSERT INTO feedback (session_id, concept_id, term, rating, comment) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (body.session_id, body.concept_id, body.term, body.rating, body.comment),
                    )
                    conn.commit()
                finally:
                    conn.close()
            return {"status": "ok", "term": body.term}
        except Exception as exc:
            logger.exception("Ошибка feedback: %s", exc)
            raise HTTPException(500, detail=f"Ошибка сохранения feedback: {exc}") from exc

    @app.post("/feedback", include_in_schema=False)
    async def feedback_legacy(request: Request, body: FeedbackRequest) -> dict:
        return await feedback_endpoint(request, body)
