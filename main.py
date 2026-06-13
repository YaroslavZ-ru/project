#!/usr/bin/env python3
"""
main.py -- точка входа AI-Terminator.

Принимает JSON двумя способами:
  1. Через stdin:     echo '{"term":"ключ"}' | python main.py
  2. Через аргумент: python main.py --input '{"term":"ключ"}'

В stdout выводится ТОЛЬКО JSON. Всё остальное -- в logs/ai_terminator.log и stderr.

CURRENT STATE (Изменение 3): заглушка -- run_pipeline возвращает фиктивные данные.
Реальные модули (preprocess, vectorize, search...) будут подключаться по мере развития проекта.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import time
import numpy as np

from src.config import Config
from src.lemmatizer import Lemmatizer
from src.synonyms import SynonymDict
from src.preprocess import preprocess
from src.embeddings import FastTextWrapper
from src.vectorize import vectorize
from src.cache import QueryVectorCache
from src.knowledge_base import KnowledgeBase
from src.aggregation import aggregate_parameters, determine_context
from src.fallback import fallback_response

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).parent
LOG_FILE: Path = PROJECT_ROOT / "logs" / "ai_terminator.log"


# ---------------------------------------------------------------------------
# Настройка логирования
# ---------------------------------------------------------------------------

def _setup_logging() -> logging.Logger:
    """Инициализирует логгер с двумя handler-ами.

    FileHandler  -- logs/ai_terminator.log, уровень DEBUG (всё детально).
    StreamHandler -- stderr, уровень WARNING (только важное).

    Returns:
        Настроенный логгер приложения.
    """
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(fmt)

    logger = logging.getLogger("ai_terminator")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


logger = _setup_logging()


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
        term, hints, debug, min_confidence,
    )

    return {
        "term": str(term).strip(),
        "hints": hints,
        "debug": debug,
        "min_confidence": min_confidence,
    }


# ---------------------------------------------------------------------------
# Пайплайн (заглушка)
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
) -> dict:
    """Центральный пайплайн обработки запроса.

    CURRENT STATE (Изменение 3): заглушка -- возвращает фиктивный ответ.
    Реальная реализация будет наполняться постепенно в изменениях 6-19.

    Args:
        term:           очищенный термин.
        hints:          список уточняющих слов/фраз.
        debug:          если True -- добавить debug_info в ответ.
        min_confidence: порог поиска (None = брать из конфига).
        cfg:            экземпляр Config (пока None).

    Returns:
        Словарь с полями: status, term, selected_context,
        parameters, suggested_refinements, warnings.
    """
    logger.info("Запуск пайплайна: term=%r hints=%r", term, hints)
    if hints is None:
        hints = []
    effective_min_confidence = min_confidence if min_confidence is not None else cfg.min_confidence

    # Шаг 1: предобработка
    processed = preprocess(term, hints, cfg, synonym_dict, lemmatizer)
    if processed["status"] == "error":
        return {"status": "error", "message": processed["message"]}
    warnings_list = list(processed.get("warnings", []))

    # Шаг 2: векторизация (с кэшем)
    query_vector = None
    if vector_cache is not None:
        query_vector = vector_cache.get(term, hints, cfg)
        if query_vector is not None:
            logger.info("Кэш-попадание вектора для: %r", term)
    if query_vector is None:
        query_vector = vectorize(processed, embedding_model)
        if vector_cache is not None:
            vector_cache.put(term, hints, cfg, query_vector)
        logger.info("Вычислен новый вектор для: %r", term)
    if np.all(query_vector == 0):
        warnings_list.append("Вектор запроса нулевой. Модель эмбеддингов недоступна. Поиск не выполнен.")

    # --- Шаг 3: Поиск кандидатов ---
    candidates: list = []
    if kb is not None and not np.all(query_vector == 0):
        t0 = time.monotonic()
        candidates = kb.search_similar_concepts(
            query_vector,
            min_confidence=effective_min_confidence,
            max_candidates=cfg.max_candidates,
        )
        logger.info("Поиск: %d кандидатов за %.3fс", len(candidates), time.monotonic() - t0)
    elif kb is None:
        warnings_list.append("KnowledgeBase не инициализирован. Поиск пропущен.")

    # --- Шаг 4: Агрегация или fallback ---
    if candidates:
        hints_lemmas = processed.get("hints_lemmas", [])
        parameters   = aggregate_parameters(candidates, hints_lemmas, cfg.max_parameters)
        selected_context      = determine_context(candidates)
        suggested_refinements = []
        if len(parameters) < 3:
            warnings_list.append(
                "Найдено мало параметров. "
                "Рекомендуется добавить уточняющие подсказки."
            )
    else:
        response = fallback_response(term, processed, cfg)
        if debug:
            response["debug_info"] = {
                "query_vector":        query_vector.tolist(),
                "candidates_raw":      [],
                "scores_distribution": [],
            }
        return response

    # --- Шаг 5: Сборка ответа ---
    result: dict = {
        "status":                "ok",
        "term":                  term,
        "selected_context":      selected_context,
        "parameters":            parameters,
        "suggested_refinements": suggested_refinements,
        "warnings":              warnings_list,
    }

    if debug:
        result["debug_info"] = {
            "query_vector":        query_vector.tolist(),
            "candidates_raw":      candidates,
            "scores_distribution": [p["confidence"] for p in parameters],
        }

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
    return synonym_dict, lemmatizer, embedding_model, vector_cache, kb

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
        ),
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="JSON-строка входных данных. Если не указано -- читать из stdin.",
    )
    args = parser.parse_args()

    # --- Загрузка конфига ---
    try:
        cfg = Config.from_json("configs/config.json", project_root=PROJECT_ROOT)
        logger.info("Конфигурация загружена: log_level=%s", cfg.log_level)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Ошибка загрузки конфига: %s", exc)
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        sys.exit(1)

    # --- Чтение входа ---
    try:
        if args.input is not None:
            raw = args.input
            logger.debug("Вход из --input")
        else:
            logger.debug("Чтение stdin...")
            raw = sys.stdin.read()

        if not raw.strip():
            raise ValueError("Входные данные пустые. Передайте JSON через --input или stdin.")

        parsed = parse_input(raw)
        synonym_dict, lemmatizer, embedding_model, vector_cache, kb = _init_components(cfg)
        logger.info("Прогрев модели...")
        _ = embedding_model.get_word_vector("а")
        logger.info("Прогрев завершён.")
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
