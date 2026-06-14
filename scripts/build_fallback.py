"""scripts/build_fallback.py -- создание data/fallback_embeddings.npy.

Собирает все уникальные слова из БД, запрашивает векторы через FastTextWrapper
и сохраняет словарь {word: np.ndarray} в .npy.
Созданный файл используется FastTextWrapper при отсутствии cc.ru.300.bin.
Запуск: python -m scripts.build_fallback [--verbose]
"""

import logging
import sqlite3
from pathlib import Path

import numpy as np

from src.config import Config
from src.embeddings import FastTextWrapper
from src.lemmatizer import Lemmatizer

logger = logging.getLogger(__name__)


def collect_words_from_db(db_path: Path, lemmatizer: Lemmatizer) -> set[str]:
    """Собирает все уникальные слова из таблиц concepts и parameters.

    Для каждого текстового поля добавляет оригинальные слова и их леммы.

    Args:
        db_path:    путь к SQLite-файлу.
        lemmatizer: экземпляр Lemmatizer.

    Returns:
        Множество уникальных слов (нижний регистр, len >= 2).
    """
    words: set[str] = set()

    def _add_text(text: str) -> None:
        if not text:
            return
        # Оригинальные слова
        for w in text.split():
            words.add(w.lower())
        # Леммы
        try:
            lemmas = lemmatizer.lemmatize_phrase(text)
            for lemma in lemmas:
                words.add(lemma.lower())
        except Exception:  # noqa: BLE001
            pass

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT term FROM concepts")
        for row in cursor.fetchall():
            _add_text(row["term"])

        cursor.execute("SELECT label_ru FROM parameters")
        for row in cursor.fetchall():
            _add_text(row["label_ru"])

        conn.close()
    except sqlite3.Error as exc:
        logger.error("Ошибка чтения БД %s: %s", db_path, exc)
        return set()

    # Фильтрация: непустые строки длиной >= 2
    return {w for w in words if len(w) >= 2}


def build_fallback(config: Config) -> dict:
    """Создаёт файл fallback_embeddings.npy.

    Args:
        config: загруженный Config.

    Returns:
        {"saved_path": str, "word_count": int} при успехе,
        {"error": str} при критической ошибке.
    """
    model_path = Path(config.fasttext_model_path)
    if not model_path.exists():
        logger.error("FastText модель не найдена: %s", model_path)
        return {"error": "fasttext_model_not_found"}

    # Сбор слов из БД
    lem = Lemmatizer(cache_size=config.cache_lemma_size)
    words = collect_words_from_db(Path(config.db_path), lem)
    if not words:
        logger.warning("База пуста или недоступна, fallback будет пустым")

    # Инициализируем FastTextWrapper БЕЗ fallback (чтобы не циклически не ссылаться)
    embedding_model = FastTextWrapper(
        model_path=model_path,
        fallback_path=None,
        cache_size=config.word_vector_cache_size,
    )

    # Собираем словарь векторов
    embedding_dict: dict[str, np.ndarray] = {}
    for word in sorted(words):  # sorted для детерминизма
        vec = embedding_model.get_word_vector(word)
        if not np.all(vec == 0):
            embedding_dict[word] = vec

    logger.info(
        "Получено векторов: %d из %d слов",
        len(embedding_dict),
        len(words),
    )

    if not embedding_dict:
        logger.warning("Словарь векторов пуст. Файл будет сохранён пустым.")

    # Определяем путь сохранения
    fb_path_str = config.fallback_embeddings_path
    if fb_path_str:
        output_path = Path(fb_path_str)
    else:
        output_path = Path(config.db_path).parent / "fallback_embeddings.npy"
        logger.warning(
            "fallback_embeddings_path не задан в конфиге. "
            "Сохраняю в %s. "
            "После запуска обновите configs/config.json.",
            output_path,
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # np.save с dict сохраняет в формате object dtype (pickle)
        # FastTextWrapper._load_fallback ожидает именно этот формат
        np.save(str(output_path), embedding_dict)
        logger.info("Фаллбак сохранён: %s", output_path)
    except PermissionError as exc:
        logger.error("Нет прав записи в %s: %s", output_path, exc)
        return {"error": "permission_denied"}
    except Exception as exc:  # noqa: BLE001
        logger.error("Ошибка сохранения: %s", exc)
        return {"error": str(exc)}

    print("\n>>> СЛЕДУЮЩИЙ ШАГ: установите в configs/config.json:")
    print(f'>>>   "fallback_embeddings_path": "{output_path}"')

    return {"saved_path": str(output_path), "word_count": len(embedding_dict)}


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path as _Path

    _root = _Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    import logging as _logging

    parser = argparse.ArgumentParser(
        description="Создаёт data/fallback_embeddings.npy из FastText + БД"
    )
    parser.add_argument(
        "--config",
        default="configs/config.json",
        help="Путь к конфигу",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Уровень DEBUG",
    )
    args = parser.parse_args()

    _log_level = _logging.DEBUG if args.verbose else _logging.INFO
    _logging.basicConfig(
        level=_log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from src.config import Config as _Config

    try:
        cfg = _Config.from_json(args.config, project_root=_root)
    except Exception as exc:
        print(f"Ошибка загрузки конфига: {exc}", file=sys.stderr)
        sys.exit(1)

    result = build_fallback(cfg)

    if "error" in result:
        print(f"Ошибка: {result['error']}", file=sys.stderr)
        sys.exit(1)

    print(f"Fallback сохранён: {result['saved_path']}")
    print(f"Слов: {result['word_count']}")
