"""src/preprocess.py -- предобработка входных данных (шаг 1 пайплайна).

Публичные имена:
  preprocess_base  -- очистка, валидация, лемматизация (без синонимов)
  preprocess_full  -- + синонимы и веса токенов
  preprocess       -- псевдоним preprocess_full (используется вне этого файла)

Формула весов токенов:
  V = 0.7 * V_term + sum(0.3/N * V_hint_i) + sum(0.1/M * V_syn_j)
  Сумма весов может превышать 1.0 -- это норма, L2-нормирование в векторизаторе.
"""
import logging
from src.config import Config
from src.lemmatizer import Lemmatizer
from src.synonyms import SynonymDict
from src.text_cleaner import clean_text

logger = logging.getLogger("ai_terminator.preprocess")


def preprocess_base(
    term: str,
    hints: list[str] | None,
    config: Config,
    lemmatizer: Lemmatizer,
) -> dict:
    """Очистка, валидация и лемматизация входных данных.

    Args:
        term:       сырая строка термина.
        hints:      список сырых подсказок (None обрабатывается как []).
        config:     объект Config.
        lemmatizer: экземпляр Lemmatizer.

    Returns:
        Словарь с полями status, original_term, original_hints, clean_term,
        clean_hints, term_lemmas, hints_lemmas, all_lemmas, warnings.
        Или {status: error, message: ...} при ошибке.
    """
    # Шаг 1. Нормализация входа
    if hints is None:
        hints = []
    if term is None:
        return {"status": "error", "message": "Термин не передан"}

    original_term = term
    original_hints = list(hints)
    warnings: list[str] = []

    # Шаг 2. Очистка термина
    clean_term = clean_text(term)
    if not clean_term:
        msg = "Термин пуст после очистки"
        logger.error("Ошибка предобработки: %s", msg)
        return {"status": "error", "message": msg}
    if len(clean_term) > config.max_term_length:
        msg = f"Термин слишком длинный: {len(clean_term)} > {config.max_term_length}"
        logger.error("Ошибка предобработки: %s", msg)
        return {"status": "error", "message": msg}

    # Шаг 3. Очистка подсказок
    raw_clean_hints = [clean_text(h) for h in hints]
    empty_count = sum(1 for h in raw_clean_hints if not h)
    if empty_count:
        warnings.append(f"Отброшено {empty_count} пустых подсказок")
        logger.warning("Отброшено %d пустых подсказок", empty_count)
    clean_hints = [h for h in raw_clean_hints if h]

    for h in clean_hints:
        if len(h) > config.max_hint_length:
            msg = f"Подсказка '…' слишком длинная: {len(h)} > {config.max_hint_length}"
            logger.error("Ошибка предобработки: %s", msg)
            return {"status": "error", "message": msg}

    unique_hints = list(dict.fromkeys(clean_hints))
    if len(unique_hints) < len(clean_hints):
        warnings.append("Обнаружены дублирующиеся подсказки, они удалены")
        logger.warning("Обнаружены дублирующиеся подсказки")
    clean_hints = unique_hints

    # Шаг 4. Лемматизация
    term_lemmas = lemmatizer.lemmatize_phrase(clean_term)
    if not term_lemmas:
        msg = "Термин не содержит значимых слов"
        logger.error("Ошибка предобработки: %s", msg)
        return {"status": "error", "message": msg}

    hints_lemmas: list[list[str]] = []
    for h in clean_hints:
        hl = lemmatizer.lemmatize_phrase(h)
        if not hl:
            warnings.append(f"Подсказка '{h}' не дала лемм")
            logger.warning("Подсказка '%s' дала пустой список лемм", h)
        hints_lemmas.append(hl)

    # Шаг 5. Сборка all_lemmas
    all_lemmas = term_lemmas + [l for sub in hints_lemmas for l in sub]

    result = {
        "status": "ok",
        "original_term": original_term,
        "original_hints": original_hints,
        "clean_term": clean_term,
        "clean_hints": clean_hints,
        "term_lemmas": term_lemmas,
        "hints_lemmas": hints_lemmas,
        "all_lemmas": all_lemmas,
        "warnings": warnings,
    }
    logger.info(
        "Предобработка завершена: term_lemmas=%r, подсказок=%d",
        term_lemmas, len(clean_hints),
    )
    return result


def preprocess_full(
    term: str,
    hints: list[str],
    config: Config,
    synonym_dict: SynonymDict,
    lemmatizer: Lemmatizer,
) -> dict:
    """Предобработка с синонимами и весами токенов.

    Возвращает все поля preprocess_base + tokens_with_weights.
    Сумма весов может превышать 1.0 -- это норма.
    L2-нормирование выполняет векторизатор (шаг 2 пайплайна).

    Args:
        term:         сырая строка термина.
        hints:        список сырых подсказок.
        config:       объект Config.
        synonym_dict: экземпляр SynonymDict.
        lemmatizer:   экземпляр Lemmatizer.

    Returns:
        Словарь со всеми полями preprocess_base + tokens_with_weights.
        Или {status: error, message: ...} при ошибке.
    """
    # Шаг 1. Базовая предобработка
    base = preprocess_base(term, hints, config, lemmatizer)
    if base["status"] == "error":
        return base

    term_lemmas: list[str] = base["term_lemmas"]
    hints_lemmas: list[list[str]] = base["hints_lemmas"]
    tokens_weights: list[tuple[str, float]] = []

    # Шаг 4. Термин: вес 0.7 / N
    term_w = 0.7 / len(term_lemmas)
    for lemma in term_lemmas:
        tokens_weights.append((lemma, round(term_w, 6)))

    # Шаг 5. Подсказки: вес 0.3 / total_hint_words
    total_hint_words = sum(len(lst) for lst in hints_lemmas)
    if total_hint_words > 0:
        hint_w = 0.3 / total_hint_words
        for sublist in hints_lemmas:
            for lemma in sublist:
                tokens_weights.append((lemma, round(hint_w, 6)))

    # Шаг 6. Синонимы
    if not config.use_synonyms:
        logger.info("Использование синонимов отключено конфигом")
    else:
        all_source = term_lemmas + [l for sub in hints_lemmas for l in sub]
        max_syn = config.max_synonyms_per_token
        unique_synonyms: set[str] = set()
        for lemma in all_source:
            for syn in synonym_dict.get_synonyms(lemma, max_syn):
                unique_synonyms.add(syn)

        # Удалить те, что уже есть в токенах
        existing = {t for t, _ in tokens_weights}
        unique_synonyms -= existing

        # Шаг 7. Добавить синонимы: вес 0.1 / M
        m = len(unique_synonyms)
        if m > 0:
            syn_w = 0.1 / m
            for syn in unique_synonyms:
                tokens_weights.append((syn, round(syn_w, 6)))
            logger.info("Добавлено %d синонимов", m)
        else:
            logger.info("Синонимы не найдены")

    # Шаг 8. Добавить поле и вернуть
    base["tokens_with_weights"] = tokens_weights
    return base


# Псевдоним: остальной код использует 'from src.preprocess import preprocess'
preprocess = preprocess_full