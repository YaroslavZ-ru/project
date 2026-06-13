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

from src.config import Config
from src.lemmatizer import Lemmatizer
from src.synonyms import SynonymDict
from src.preprocess import preprocess

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
    hints: list[str],
    debug: bool,
    min_confidence: float | None,
    cfg: Config,
    lemmatizer: Lemmatizer | None = None,
    synonym_dict: SynonymDict | None = None,
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

    # Шаг 1: предобработка
    processed = preprocess(term, hints, cfg, synonym_dict, lemmatizer)
    if processed["status"] == "error":
        return {
            "status": "error",
            "message": processed["message"],
        }

    # Шаги 2-5 будут добавлены по мере реализации векторизации и поиска
    result: dict = {
        "status": "ok",
        "term": processed["clean_term"],
        "selected_context": {"domain": "не определено", "confidence": 0.0},
        "parameters": [],
        "suggested_refinements": [],
        "warnings": processed.get("warnings", []),
    }

    if debug:
        result["debug_info"] = {
            "hints_received": hints,
            "min_confidence_used": min_confidence,
            "pipeline_stage": "заглушка (изменение 3)",
        }

    logger.debug("Пайплайн завершён: %r", result)
    return result


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

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

    lemmatizer = Lemmatizer(cache_size=cfg.cache_lemma_size)
    synonym_dict = SynonymDict(json_path=cfg.synonyms_path)

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
        result = run_pipeline(
            term=parsed["term"],
            hints=parsed["hints"],
            debug=parsed["debug"],
            min_confidence=parsed["min_confidence"],
            cfg=cfg,
            lemmatizer=lemmatizer,
            synonym_dict=synonym_dict,
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
