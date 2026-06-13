"""src/preprocess.py -- \u043f\u0440\u0435\u0434\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0432\u0445\u043e\u0434\u043d\u044b\u0445 \u0434\u0430\u043d\u043d\u044b\u0445 (\u0448\u0430\u0433 1 \u043f\u0430\u0439\u043f\u043b\u0430\u0439\u043d\u0430).

\u041f\u0443\u0431\u043b\u0438\u0447\u043d\u044b\u0435 \u0438\u043c\u0435\u043d\u0430:
  preprocess_base  -- \u043e\u0447\u0438\u0441\u0442\u043a\u0430, \u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u044f, \u043b\u0435\u043c\u043c\u0430\u0442\u0438\u0437\u0430\u0446\u0438\u044f (\u0431\u0435\u0437 \u0441\u0438\u043d\u043e\u043d\u0438\u043c\u043e\u0432)
  preprocess_full  -- + \u0441\u0438\u043d\u043e\u043d\u0438\u043c\u044b \u0438 \u0432\u0435\u0441\u0430 \u0442\u043e\u043a\u0435\u043d\u043e\u0432
  preprocess       -- \u043f\u0441\u0435\u0432\u0434\u043e\u043d\u0438\u043c preprocess_full (\u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f \u0432\u043d\u0435 \u044d\u0442\u043e\u0433\u043e \u0444\u0430\u0439\u043b\u0430)

\u0424\u043e\u0440\u043c\u0443\u043b\u0430 \u0432\u0435\u0441\u043e\u0432 \u0442\u043e\u043a\u0435\u043d\u043e\u0432:
  V = 0.7 * V_term + sum(0.3/N * V_hint_i) + sum(0.1/M * V_syn_j)
  \u0421\u0443\u043c\u043c\u0430 \u0432\u0435\u0441\u043e\u0432 \u043c\u043e\u0436\u0435\u0442 \u043f\u0440\u0435\u0432\u044b\u0448\u0430\u0442\u044c 1.0 -- \u044d\u0442\u043e \u043d\u043e\u0440\u043c\u0430, L2-\u043d\u043e\u0440\u043c\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0432 \u0432\u0435\u043a\u0442\u043e\u0440\u0438\u0437\u0430\u0442\u043e\u0440\u0435.
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
    """\u041e\u0447\u0438\u0441\u0442\u043a\u0430, \u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u044f \u0438 \u043b\u0435\u043c\u043c\u0430\u0442\u0438\u0437\u0430\u0446\u0438\u044f \u0432\u0445\u043e\u0434\u043d\u044b\u0445 \u0434\u0430\u043d\u043d\u044b\u0445.

    Args:
        term:       \u0441\u044b\u0440\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430 \u0442\u0435\u0440\u043c\u0438\u043d\u0430.
        hints:      \u0441\u043f\u0438\u0441\u043e\u043a \u0441\u044b\u0440\u044b\u0445 \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043e\u043a (None \u043e\u0431\u0440\u0430\u0431\u0430\u0442\u044b\u0432\u0430\u0435\u0442\u0441\u044f \u043a\u0430\u043a []).
        config:     \u043e\u0431\u044a\u0435\u043a\u0442 Config.
        lemmatizer: \u044d\u043a\u0437\u0435\u043c\u043f\u043b\u044f\u0440 Lemmatizer.

    Returns:
        \u0421\u043b\u043e\u0432\u0430\u0440\u044c \u0441 \u043f\u043e\u043b\u044f\u043c\u0438 status, original_term, original_hints, clean_term,
        clean_hints, term_lemmas, hints_lemmas, all_lemmas, warnings.
        \u0418\u043b\u0438 {status: error, message: ...} \u043f\u0440\u0438 \u043e\u0448\u0438\u0431\u043a\u0435.
    """
    # \u0428\u0430\u0433 1. \u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0432\u0445\u043e\u0434\u0430
    if hints is None:
        hints = []
    if term is None:
        return {"status": "error", "message": "\u0422\u0435\u0440\u043c\u0438\u043d \u043d\u0435 \u043f\u0435\u0440\u0435\u0434\u0430\u043d"}

    original_term = term
    original_hints = list(hints)
    warnings: list[str] = []

    # \u0428\u0430\u0433 2. \u041e\u0447\u0438\u0441\u0442\u043a\u0430 \u0442\u0435\u0440\u043c\u0438\u043d\u0430
    clean_term = clean_text(term)
    if not clean_term:
        msg = "\u0422\u0435\u0440\u043c\u0438\u043d \u043f\u0443\u0441\u0442 \u043f\u043e\u0441\u043b\u0435 \u043e\u0447\u0438\u0441\u0442\u043a\u0438"
        logger.error("\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0435\u0434\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438: %s", msg)
        return {"status": "error", "message": msg}
    if len(clean_term) > config.max_term_length:
        msg = f"\u0422\u0435\u0440\u043c\u0438\u043d \u0441\u043b\u0438\u0448\u043a\u043e\u043c \u0434\u043b\u0438\u043d\u043d\u044b\u0439: {len(clean_term)} > {config.max_term_length}"
        logger.error("\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0435\u0434\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438: %s", msg)
        return {"status": "error", "message": msg}

    # \u0428\u0430\u0433 3. \u041e\u0447\u0438\u0441\u0442\u043a\u0430 \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043e\u043a
    raw_clean_hints = [clean_text(h) for h in hints]
    empty_count = sum(1 for h in raw_clean_hints if not h)
    if empty_count:
        warnings.append(f"\u041e\u0442\u0431\u0440\u043e\u0448\u0435\u043d\u043e {empty_count} \u043f\u0443\u0441\u0442\u044b\u0445 \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043e\u043a")
        logger.warning("\u041e\u0442\u0431\u0440\u043e\u0448\u0435\u043d\u043e %d \u043f\u0443\u0441\u0442\u044b\u0445 \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043e\u043a", empty_count)
    clean_hints = [h for h in raw_clean_hints if h]

    for h in clean_hints:
        if len(h) > config.max_hint_length:
            msg = f"\u041f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0430 '\u2026' \u0441\u043b\u0438\u0448\u043a\u043e\u043c \u0434\u043b\u0438\u043d\u043d\u0430\u044f: {len(h)} > {config.max_hint_length}"
            logger.error("\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0435\u0434\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438: %s", msg)
            return {"status": "error", "message": msg}

    unique_hints = list(dict.fromkeys(clean_hints))
    if len(unique_hints) < len(clean_hints):
        warnings.append("\u041e\u0431\u043d\u0430\u0440\u0443\u0436\u0435\u043d\u044b \u0434\u0443\u0431\u043b\u0438\u0440\u0443\u044e\u0449\u0438\u0435\u0441\u044f \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0438, \u043e\u043d\u0438 \u0443\u0434\u0430\u043b\u0435\u043d\u044b")
        logger.warning("\u041e\u0431\u043d\u0430\u0440\u0443\u0436\u0435\u043d\u044b \u0434\u0443\u0431\u043b\u0438\u0440\u0443\u044e\u0449\u0438\u0435\u0441\u044f \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0438")
    clean_hints = unique_hints

    # \u0428\u0430\u0433 4. \u041b\u0435\u043c\u043c\u0430\u0442\u0438\u0437\u0430\u0446\u0438\u044f
    term_lemmas = lemmatizer.lemmatize_phrase(clean_term)
    if not term_lemmas:
        msg = "\u0422\u0435\u0440\u043c\u0438\u043d \u043d\u0435 \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442 \u0437\u043d\u0430\u0447\u0438\u043c\u044b\u0445 \u0441\u043b\u043e\u0432"
        logger.error("\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0435\u0434\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438: %s", msg)
        return {"status": "error", "message": msg}

    hints_lemmas: list[list[str]] = []
    for h in clean_hints:
        hl = lemmatizer.lemmatize_phrase(h)
        if not hl:
            warnings.append(f"\u041f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0430 '{h}' \u043d\u0435 \u0434\u0430\u043b\u0430 \u043b\u0435\u043c\u043c")
            logger.warning("\u041f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0430 '%s' \u0434\u0430\u043b\u0430 \u043f\u0443\u0441\u0442\u043e\u0439 \u0441\u043f\u0438\u0441\u043e\u043a \u043b\u0435\u043c\u043c", h)
        hints_lemmas.append(hl)

    # \u0428\u0430\u0433 5. \u0421\u0431\u043e\u0440\u043a\u0430 all_lemmas
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
        "\u041f\u0440\u0435\u0434\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430: term_lemmas=%r, \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043e\u043a=%d",
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
    """\u041f\u0440\u0435\u0434\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0441 \u0441\u0438\u043d\u043e\u043d\u0438\u043c\u0430\u043c\u0438 \u0438 \u0432\u0435\u0441\u0430\u043c\u0438 \u0442\u043e\u043a\u0435\u043d\u043e\u0432.

    \u0412\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u0442 \u0432\u0441\u0435 \u043f\u043e\u043b\u044f preprocess_base + tokens_with_weights.
    \u0421\u0443\u043c\u043c\u0430 \u0432\u0435\u0441\u043e\u0432 \u043c\u043e\u0436\u0435\u0442 \u043f\u0440\u0435\u0432\u044b\u0448\u0430\u0442\u044c 1.0 -- \u044d\u0442\u043e \u043d\u043e\u0440\u043c\u0430.
    L2-\u043d\u043e\u0440\u043c\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0432\u044b\u043f\u043e\u043b\u043d\u044f\u0435\u0442 \u0432\u0435\u043a\u0442\u043e\u0440\u0438\u0437\u0430\u0442\u043e\u0440 (\u0448\u0430\u0433 2 \u043f\u0430\u0439\u043f\u043b\u0430\u0439\u043d\u0430).

    Args:
        term:         \u0441\u044b\u0440\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430 \u0442\u0435\u0440\u043c\u0438\u043d\u0430.
        hints:        \u0441\u043f\u0438\u0441\u043e\u043a \u0441\u044b\u0440\u044b\u0445 \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043e\u043a.
        config:       \u043e\u0431\u044a\u0435\u043a\u0442 Config.
        synonym_dict: \u044d\u043a\u0437\u0435\u043c\u043f\u043b\u044f\u0440 SynonymDict.
        lemmatizer:   \u044d\u043a\u0437\u0435\u043c\u043f\u043b\u044f\u0440 Lemmatizer.

    Returns:
        \u0421\u043b\u043e\u0432\u0430\u0440\u044c \u0441\u043e \u0432\u0441\u0435\u043c\u0438 \u043f\u043e\u043b\u044f\u043c\u0438 preprocess_base + tokens_with_weights.
        \u0418\u043b\u0438 {status: error, message: ...} \u043f\u0440\u0438 \u043e\u0448\u0438\u0431\u043a\u0435.
    """
    # \u0428\u0430\u0433 1. \u0411\u0430\u0437\u043e\u0432\u0430\u044f \u043f\u0440\u0435\u0434\u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430
    base = preprocess_base(term, hints, config, lemmatizer)
    if base["status"] == "error":
        return base

    term_lemmas: list[str] = base["term_lemmas"]
    hints_lemmas: list[list[str]] = base["hints_lemmas"]
    tokens_weights: list[tuple[str, float]] = []

    # \u0428\u0430\u0433 4. \u0422\u0435\u0440\u043c\u0438\u043d: \u0432\u0435\u0441 0.7 / N
    term_w = 0.7 / len(term_lemmas)
    for lemma in term_lemmas:
        tokens_weights.append((lemma, round(term_w, 6)))

    # \u0428\u0430\u0433 5. \u041f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0438: \u0432\u0435\u0441 0.3 / total_hint_words
    total_hint_words = sum(len(lst) for lst in hints_lemmas)
    if total_hint_words > 0:
        hint_w = 0.3 / total_hint_words
        for sublist in hints_lemmas:
            for lemma in sublist:
                tokens_weights.append((lemma, round(hint_w, 6)))

    # \u0428\u0430\u0433 6. \u0421\u0438\u043d\u043e\u043d\u0438\u043c\u044b
    if not config.use_synonyms:
        logger.info("\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u0435 \u0441\u0438\u043d\u043e\u043d\u0438\u043c\u043e\u0432 \u043e\u0442\u043a\u043b\u044e\u0447\u0435\u043d\u043e \u043a\u043e\u043d\u0444\u0438\u0433\u043e\u043c")
    else:
        all_source = term_lemmas + [l for sub in hints_lemmas for l in sub]
        max_syn = config.max_synonyms_per_token
        unique_synonyms: set[str] = set()
        for lemma in all_source:
            for syn in synonym_dict.get_synonyms(lemma, max_syn):
                unique_synonyms.add(syn)

        # \u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0442\u0435, \u0447\u0442\u043e \u0443\u0436\u0435 \u0435\u0441\u0442\u044c \u0432 \u0442\u043e\u043a\u0435\u043d\u0430\u0445
        existing = {t for t, _ in tokens_weights}
        unique_synonyms -= existing

        # \u0428\u0430\u0433 7. \u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u0438\u043d\u043e\u043d\u0438\u043c\u044b: \u0432\u0435\u0441 0.1 / M
        m = len(unique_synonyms)
        if m > 0:
            syn_w = 0.1 / m
            for syn in unique_synonyms:
                tokens_weights.append((syn, round(syn_w, 6)))
            logger.info("\u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e %d \u0441\u0438\u043d\u043e\u043d\u0438\u043c\u043e\u0432", m)
        else:
            logger.info("\u0421\u0438\u043d\u043e\u043d\u0438\u043c\u044b \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b")

    # \u0428\u0430\u0433 8. \u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u043e\u043b\u0435 \u0438 \u0432\u0435\u0440\u043d\u0443\u0442\u044c
    base["tokens_with_weights"] = tokens_weights
    return base


# \u041f\u0441\u0435\u0432\u0434\u043e\u043d\u0438\u043c: \u043e\u0441\u0442\u0430\u043b\u044c\u043d\u043e\u0439 \u043a\u043e\u0434 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442 'from src.preprocess import preprocess'
preprocess = preprocess_full