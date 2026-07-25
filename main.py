#!/usr/bin/env python3
"""
main.py -- точка входа AI-Terminator.

Принимает JSON двумя способами:
  1. Через stdin:     echo '{"term":"ключ"}' | python main.py
  2. Через аргумент: python main.py --input '{"term":"ключ"}'

В stdout выводится ТОЛЬКО JSON. Всё остальное -- в logs/ai_terminator.log и stderr.

CURRENT STATE: run_pipeline полностью реализован (Изменения 1-24).
Все модули подключены: preprocess, vectorize, search, aggregation, sessions, generative.
"""

import argparse
import json
import logging
import os
from pathlib import Path
import sys
import time

import numpy as np

from src.aggregation import (
    aggregate_parameters,
    apply_feedback_correction,
    detect_ambiguity,
    determine_context,
    generate_clarification_questions,
)
from src.cache import QueryVectorCache
from src.config import Config
from src.embeddings import FastTextWrapper
from src.fallback import fallback_response
from src.generative import GenerativeExpander
from src.knowledge_base import KnowledgeBase
from src.lemmatizer import Lemmatizer
from src.observability import RequestTraceContext, generate_request_id, get_default_trace_context
from src.preprocess import preprocess
from src.sessions import SessionManager
from src.synonyms import SynonymDict
from src.vectorize import vectorize

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).parent
LOG_FILE: Path = PROJECT_ROOT / "logs" / "ai_terminator.log"


# ---------------------------------------------------------------------------
# Настройка логирования
# ---------------------------------------------------------------------------


def _setup_logging(log_level: str = "INFO", log_format: str = "text") -> logging.Logger:
    """Инициализировать логгер с StreamHandler и RotatingFileHandler.

    Args:
        log_level:  уровень логирования (из конфига, например DEBUG).
        log_format: формат логов "text" или "json" (изм. 65).

    Returns:
        Настроенный логгер приложения.
    """
    from src.utils import JSONFormatter

    LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    if log_format == "json":
        fmt = JSONFormatter()
    else:
        fmt = logging.Formatter(LOG_FORMAT, DATE_FMT)

    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("ai_terminator")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logs_dir = LOG_FILE.parent
    if logs_dir.exists() and os.access(str(logs_dir), os.W_OK):
        try:
            from logging.handlers import RotatingFileHandler

            fh = RotatingFileHandler(
                str(LOG_FILE),
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            fh.setFormatter(fmt)
            logger.addHandler(fh)
            logger.debug("Логирование в файл: %s", LOG_FILE)
        except (OSError, PermissionError) as exc:
            logger.warning("Не удалось создать файловый лог: %s", exc)
    else:
        logger.debug("logs/ недоступна — только консоль")

    return logger


logger = _setup_logging(log_level="INFO", log_format="text")


def _reconfigure_logging(log_level: str = "INFO", log_format: str = "text") -> None:
    """Переконфигурировать существующий логгер (изм. 65).

    Заменяет форматтеры во всех обработчиках root-логгера.
    Используется после загрузки конфига, когда известен log_format.
    """
    from src.utils import JSONFormatter

    LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    if log_format == "json":
        fmt = JSONFormatter()
    else:
        fmt = logging.Formatter(LOG_FORMAT, DATE_FMT)

    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(fmt)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))


# ---------------------------------------------------------------------------
# Парсинг входных данных
# ---------------------------------------------------------------------------


def parse_input(raw: str) -> dict:
    """Парсит и нормализует входной JSON.

    Args:
        raw: строка с JSON-объектом.

    Returns:
        Нормализованный словарь с полями:
          - term (str)
          - hints (list[str])
          - debug (bool)
          - min_confidence (float | None)

    Raises:
        ValueError: если JSON невалиден или отсутствует / пуст term.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Невалидный JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Вход должен быть JSON-объектом, не массивом")

    # term -- обязательное поле
    term = data.get("term")
    if not term or not str(term).strip():
        raise ValueError("Поле 'term' обязательно и не должно быть пустым")

    # hints -- если null или отсутствует -- пустой список
    hints = data.get("hints")
    if hints is None:
        hints = []

    # debug -- если отсутствует -- False
    debug: bool = bool(data.get("debug", False))

    # min_confidence -- если отсутствует -- None (будет взято из конфига)
    min_confidence: float | None = data.get("min_confidence", None)

    logger.debug(
        "Парсинг входа: term=%r hints=%r debug=%s min_confidence=%s",
        term,
        hints,
        debug,
        min_confidence,
    )

    session_id: str | None = data.get("session_id", None)

    return {
        "term": str(term).strip(),
        "hints": hints,
        "debug": debug,
        "min_confidence": min_confidence,
        "session_id": session_id,
    }


# ---------------------------------------------------------------------------
# Пайплайн
# ---------------------------------------------------------------------------


def run_pipeline(
    term: str,
    hints,
    debug: bool,
    min_confidence,
    cfg: Config,
    lemmatizer=None,
    synonym_dict=None,
    embedding_model=None,
    vector_cache=None,
    kb=None,
    generative_expander=None,
    session_manager=None,
    session_id: str | None = None,
    request_id: str | None = None,
    trace_context: RequestTraceContext | None = None,
) -> dict:
    """Центральный пайплайн обработки запроса.

    Центральный пайплайн обработки запроса (Изменения 1-24).
    Все шаги реализованы: предобработка, векторизация, поиск, агрегация,
    генеративное расширение (опционально), сессии.
    Args:
        term:           очищенный термин.
        hints:          список уточняющих слов/фраз.
        debug:          если True -- добавить debug_info в ответ.
        min_confidence: порог поиска (None = брать из конфига).
        cfg:            экземпляр Config (пока None).
        request_id:     уникальный ID запроса для трассировки.
        trace_context:  контекст трассировки для фиксации этапов.

    Returns:
        Словарь с полями: status, term, selected_context,
        parameters, suggested_refinements, warnings, request_id, trace.
    """
    logger.info("Запуск пайплайна: term=%r hints=%r request_id=%s", term, hints, request_id[:8] if request_id else "?")
    if hints is None:
        hints = []

    # Создать контекст трассировки, если не передан
    if trace_context is None:
        trace_context = get_default_trace_context(request_id)
        request_id = trace_context.request_id

    # --- Блок B: Центроид сессии ---
    session_hint_domain: str | None = None
    if session_id and session_manager and kb is not None:
        _saved = session_manager.get_domain(session_id)
        if _saved:
            session_hint_domain = _saved
            logger.debug("Сессия %r: сохранённый домен %r", session_id, _saved)

    # Загрузка домена из сессии
    if session_id and session_manager:
        saved_domain = session_manager.get_domain(session_id)
        if saved_domain:
            logger.debug("Использую домен из сессии %r: %s", session_id, saved_domain)
    effective_min_confidence = min_confidence if min_confidence is not None else cfg.min_confidence

    # Шаг 1: предобработка
    t_stage = time.monotonic()
    processed = preprocess(term, hints, cfg, synonym_dict, lemmatizer)
    trace_context.add_stage("preprocess", time.monotonic() - t_stage, {"lemmas": len(processed.get("all_lemmas", []))})
    if processed["status"] == "error":
        return {"status": "error", "message": processed["message"], "request_id": request_id}
    warnings_list = list(processed.get("warnings", []))

    # Шаг 2: векторизация (с кэшем)
    t_stage = time.monotonic()
    query_vector = None
    cache_hit = False
    if vector_cache is not None:
        query_vector = vector_cache.get(term, hints, cfg)
        if query_vector is not None:
            cache_hit = True
            logger.info("Кэш-попадание вектора для: %r", term)
    if query_vector is None:
        query_vector = vectorize(processed, embedding_model)
        if vector_cache is not None:
            vector_cache.put(term, hints, cfg, query_vector)
        logger.info("Вычислен новый вектор для: %r", term)
    trace_context.add_stage("vectorize", time.monotonic() - t_stage, {"cache_hit": cache_hit})
    if np.all(query_vector == 0):
        warnings_list.append(
            "Вектор запроса нулевой. Модель эмбеддингов недоступна. Поиск не выполнен."
        )

    # --- Проверка центроида сессии после vectorize ---
    if session_hint_domain and kb is not None and not np.all(query_vector == 0):
        domain_centroids = kb.load_domain_centroids()
        if domain_centroids:
            closest = kb.get_closest_domain(query_vector, domain_centroids)
            if closest and closest != session_hint_domain:
                logger.info(
                    "Запрос %r ближе к домену %r (сессия: %r)",
                    term,
                    closest,
                    session_hint_domain,
                )
                session_hint_domain = closest
            elif closest == session_hint_domain:
                logger.debug("Запрос %r подтверждает домен сессии %r", term, session_hint_domain)

    # --- Шаг 3: Поиск кандидатов ---
    t_stage = time.monotonic()
    candidates: list = []
    if kb is not None and not np.all(query_vector == 0):
        candidates = kb.search_similar_concepts(
            query_vector,
            min_confidence=effective_min_confidence,
            max_candidates=cfg.max_candidates,
        )
    elif kb is None:
        warnings_list.append("KnowledgeBase не инициализирован. Поиск пропущен.")
    trace_context.add_stage("search", time.monotonic() - t_stage, {"candidates_count": len(candidates)})
    logger.info("Поиск: %d кандидатов за %.3fс", len(candidates), time.monotonic() - t_stage)

    # --- Фильтрация домена по hints (раздел 19.1 описания) ---
    # Если hints однозначно указывают на домен — фильтруем кандидатов.
    # Это предотвращает false-positive "ambiguous" когда hint уже разрешил домен.
    hint_domain: str | None = None
    if candidates and hints:
        hints_lemmas_flat = [lemma for sub in processed.get("hints_lemmas", []) for lemma in sub]
        if hints_lemmas_flat:
            from src.fallback import detect_domain
            hint_domain = detect_domain(set(hints_lemmas_flat), cfg.fallback_domain_keywords_path)
            if hint_domain and hint_domain != "general":
                filtered = [c for c in candidates if c.get("domain") == hint_domain]
                if filtered:
                    candidates = filtered
                    logger.info("Hints '%s' -> домен '%s', отфильтровано %d кандидатов",
                                hints, hint_domain, len(candidates))
                else:
                    hint_domain = None
                    logger.debug("Hints '%s' -> домен '%s', но кандидатов в домене нет", hints, hint_domain)

    # --- Проверка минимального confidence ---
    # Если лучший кандидат имеет很低 confidence — считаем что термин не найден,
    # переходим в fallback (шаблонные параметры).
    if candidates:
        best_sim = max(c.get("similarity", 0.0) for c in candidates)
        if best_sim < 0.3:
            logger.info("Лучший кандидат: %.4f < 0.3, переход в fallback для %r", best_sim, term)
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

    # --- Шаг 4: Агрегация или fallback ---
    t_stage = time.monotonic()
    if candidates:
        hints_lemmas = processed.get("hints_lemmas", [])

        # Сначала определяем контекст для ambiguity detection (без фильтрации)
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
            logger.info(
                "Обнаружена неоднозначность для %r: %s vs %s",
                term,
                ambiguity_info["top_domain"],
                ambiguity_info["runner_up"],
            )
        else:
            # Неоднозначности нет — фильтруем кандидатов по домену
            primary_domain = selected_context.get("domain")
            if primary_domain and primary_domain != "не определено":
                domain_filtered = [c for c in candidates if c.get("domain") == primary_domain]
                if domain_filtered:
                    candidates = domain_filtered

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
        suggested_refinements = []

        # Генеративное расширение при нехватке параметров
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
                logger.info("Генеративное расширение: +%d параметров", len(gen_params))

        if len(parameters) < 3:
            warnings_list.append(
                "Найдено мало параметров. Рекомендуется добавить уточняющие подсказки."
            )
    else:
        needs_clarification = False
        response = fallback_response(term, processed, cfg)
        response["needs_clarification"] = False
        response["request_id"] = request_id
        if debug:
            response["debug_info"] = {
                "query_vector": query_vector.tolist(),
                "candidates_raw": [],
                "scores_distribution": [],
            }
            response["trace"] = trace_context.to_dict()
        trace_context.add_stage("aggregation", time.monotonic() - t_stage, {"fallback": True})
        return response
    trace_context.add_stage("aggregation", time.monotonic() - t_stage, {"parameters_count": len(parameters)})

    # --- Шаг 5: Сборка ответа ---
    if needs_clarification:
        # Раздел 19.2 описания: при ambiguous — пустые параметры,
        # selected_context содержит domain_candidates
        result: dict = {
            "status": "ambiguous",
            "term": term,
            "selected_context": {
                "domain_candidates": ambiguity_info.get("domain_candidates", []),
            },
            "needs_clarification": True,
            "parameters": [],
            "suggested_refinements": suggested_refinements,
            "warnings": warnings_list,
            "request_id": request_id,
        }
    else:
        result = {
            "status": "ok",
            "term": term,
            "selected_context": selected_context,
            "needs_clarification": False,
            "parameters": parameters,
            "suggested_refinements": suggested_refinements,
            "warnings": warnings_list,
            "request_id": request_id,
        }

    if debug:
        result["debug_info"] = {
            "query_vector": query_vector.tolist(),
            "candidates_raw": candidates,
            "scores_distribution": [p["confidence"] for p in parameters],
        }
        result["trace"] = trace_context.to_dict()

    # Сохранение домена в сессию
    if session_manager and session_id:
        result_status = result.get("status", "")
        result_domain = result.get("selected_context", {}).get("domain")
        if (
            result_status == "ok"
            and cfg.auto_save_domain_on_ok
            and result_domain
            or (result_status == "ok" and cfg.auto_save_domain_on_fallback and result_domain)
        ):
            session_manager.update_session(session_id, result_domain, term)

    logger.debug("Пайплайн завершён: %r", result)
    return result


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------


def _init_components(cfg):
    lemmatizer = Lemmatizer(cache_size=cfg.cache_lemma_size)
    synonym_dict = SynonymDict(json_path=cfg.synonyms_path)
    fallback_path = cfg.fallback_embeddings_path if cfg.fallback_embeddings_path else None
    embedding_model = FastTextWrapper(
        model_path=cfg.fasttext_model_path,
        fallback_path=fallback_path,
        cache_size=cfg.word_vector_cache_size,
    )
    vector_cache = QueryVectorCache(maxsize=cfg.query_cache_size)
    kb = KnowledgeBase(
        config=cfg,
        embedding_model=embedding_model,
        synonym_dict=synonym_dict,
    )
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


def main() -> None:
    """Читает вход, запускает пайплайн, выводит JSON в stdout.

    Ошибки перехватываются и возвращаются как {"status": "error", "message": "..."}.
    Завершается sys.exit(1) при ошибке.
    """
    # --- Аргументы командной строки ---
    parser = argparse.ArgumentParser(
        description="AI-Terminator: генерация параметров для термина",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Примеры:\n"
            '  echo \'{"term":"ключ"}\'  | python main.py\n'
            '  python main.py --input \'{"term":"ключ", "hints":["техника"]}\' \n'
            '  echo \'{"term":"ключ"}\' | python main.py --once\n'
        ),
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="JSON-строка входных данных. Если не указано -- читать из stdin.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.json",
        help="Путь к файлу конфигурации (default: configs/config.json)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Включить debug=True для всех запросов",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Обработать один запрос и выйти (без цикла)",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        choices=["development", "production", "test"],
        help="Окружение: development, production, test",
    )
    args = parser.parse_args()

    # --- Загрузка конфига ---
    try:
        if args.env:
            cfg = Config.for_environment(args.env, project_root=PROJECT_ROOT)
        else:
            cfg = Config.from_json(args.config, project_root=PROJECT_ROOT)
        logger.info("Конфигурация загружена: log_level=%s", cfg.log_level)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Ошибка загрузки конфига: %s", exc)
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        sys.exit(1)

    # Изменение 65: Переопределение логирования с учётом log_format из конфига
    log_format = getattr(cfg, "log_format", "text")
    if log_format != "text":
        _reconfigure_logging(log_level=cfg.log_level, log_format=log_format)

    # --- Чтение входа ---
    try:
        if args.input is not None:
            raw = args.input
            logger.debug("Вход из --input")
        elif args.once:
            raw = sys.stdin.readline().strip()
            if not raw:
                sys.exit(0)
            logger.debug("Вход из stdin (once)")
        else:
            logger.debug("Чтение stdin...")
            raw = sys.stdin.read()

        if not raw.strip():
            raise ValueError("Входные данные пустые. Передайте JSON через --input или stdin.")

        parsed = parse_input(raw)
        (
            synonym_dict,
            lemmatizer,
            embedding_model,
            vector_cache,
            kb,
            generative_expander,
            session_manager,
        ) = _init_components(cfg)
        logger.info("Прогрев модели...")
        _ = embedding_model.get_word_vector("а")
        logger.info("Прогрев завершён.")
        request_id = generate_request_id()
        result = run_pipeline(
            term=parsed["term"],
            hints=parsed.get("hints", []),
            debug=parsed.get("debug", False),
            min_confidence=parsed.get("min_confidence"),
            cfg=cfg,
            lemmatizer=lemmatizer,
            synonym_dict=synonym_dict,
            embedding_model=embedding_model,
            vector_cache=vector_cache,
            kb=kb,
            generative_expander=generative_expander,
            session_manager=session_manager,
            session_id=parsed.get("session_id"),
            request_id=request_id,
        )

    except ValueError as exc:
        logger.warning("Ошибка входных данных: %s", exc)
        result = {"status": "error", "message": str(exc)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Непредвиденная ошибка: %s", exc)
        result = {"status": "error", "message": f"Внутренняя ошибка: {exc}"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    # --- Вывод в stdout (только JSON, ничего лишнего) ---
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
