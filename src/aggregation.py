import logging

import numpy as np

from src.lemmatizer import Lemmatizer

logger = logging.getLogger(__name__)


# --- Изменение 63: Детекция несвязных подсказок ---


def check_hints_coherence(
    hints: list[str],
    embedding_model,
    threshold: float = 0.2,
) -> dict:
    """Проверить семантическую связность подсказок.

    Вычисляет косинусное сходство между векторами подсказок и сравнивает
    среднее значение с порогом. Если среднее сходство ниже порога,
    подсказки считаются несвязными.

    Args:
        hints:          список подсказок (1-3 слова/фразы).
        embedding_model: модель эмбеддингов (FastTextWrapper или мок с get_phrase_vector).
        threshold:      порог связности (по умолчанию 0.2).

    Returns:
        Словарь с полями:
            coherent:       bool — True если связны, False если нет.
            avg_similarity: float — среднее косинусное сходство по парам.
            pairs:          list[dict] — информация по каждой паре.
            reason:         str — описание результата.
    """
    if len(hints) < 2:
        return {
            "coherent": True,
            "avg_similarity": 1.0,
            "pairs": [],
            "reason": "недостаточно подсказок для проверки",
        }

    pairs: list[dict] = []
    for i in range(len(hints)):
        for j in range(i + 1, len(hints)):
            vec_i = embedding_model.get_phrase_vector(hints[i])
            vec_j = embedding_model.get_phrase_vector(hints[j])
            norm_i = float(np.linalg.norm(vec_i))
            norm_j = float(np.linalg.norm(vec_j))
            if norm_i > 1e-9 and norm_j > 1e-9:
                sim = float(np.dot(vec_i, vec_j) / (norm_i * norm_j))
            else:
                sim = 0.0
            pairs.append({"hint_i": hints[i], "hint_j": hints[j], "similarity": round(sim, 4)})

    avg_sim = sum(p["similarity"] for p in pairs) / len(pairs) if pairs else 0.0

    if avg_sim < threshold:
        return {
            "coherent": False,
            "avg_similarity": round(avg_sim, 4),
            "pairs": pairs,
            "reason": (
                f"Среднее сходство подсказок ({avg_sim:.2f}) "
                f"ниже порога ({threshold})"
            ),
        }

    return {
        "coherent": True,
        "avg_similarity": round(avg_sim, 4),
        "pairs": pairs,
        "reason": "подсказки связаны",
    }


def _compute_hint_match(param: dict, hint_set: set) -> float:
    if not hint_set:
        return 0.0
    text = (param.get("label_ru", "") + " " + param.get("description", "")).lower()
    lem = Lemmatizer()
    param_lemmas = set(lem.lemmatize_phrase(text))
    return len(hint_set & param_lemmas) / len(hint_set)


def aggregate_parameters(
    candidates: list,
    hints_lemmas: list,
    max_parameters: int,
) -> list:
    if not candidates:
        return []

    groups: dict = {}
    for candidate in candidates:
        sim = candidate["similarity"]
        for param in candidate.get("parameters", []):
            name = param["name"]
            if name not in groups:
                groups[name] = {
                    "param": param.copy(),
                    "similarities": [],
                    "freq": 0,
                }
            groups[name]["similarities"].append(sim)
            groups[name]["freq"] += 1

    if not groups:
        return []

    # Определяем лучшего кандидата (максимальная similarity)
    top_sim = max(candidate["similarity"] for candidate in candidates)

    # Убираем параметры, которые пришли ТОЛЬКО от слабых кандидатов (< 85% от лучшего)
    weak_threshold = top_sim * 0.85
    groups = {
        name: g for name, g in groups.items()
        if max(g["similarities"]) >= weak_threshold
    }
    if not groups:
        return []

    max_freq = max(g["freq"] for g in groups.values())
    n_candidates = len(candidates)
    hint_set = {lemma for sub in hints_lemmas for lemma in sub}

    for g in groups.values():
        # freq_norm: доля кандидатов, содержащих этот параметр (0.0 - 1.0)
        freq_norm = g["freq"] / n_candidates if n_candidates > 0 else 0.0
        avg_sim = sum(g["similarities"]) / len(g["similarities"])
        hint_match = _compute_hint_match(g["param"], hint_set)

        # Специфичность: параметр от лучшего кандидата — бонус,
        # параметр от слабого кандидата (< 85% от лучшего) — штраф.
        max_sim = max(g["similarities"])
        if max_sim >= top_sim * 0.95:
            specificity = 1.3  # от лучшего кандидата
        elif max_sim >= top_sim * 0.85:
            specificity = 1.0  # от похожего кандидата
        else:
            specificity = 0.3  # от слабого кандидата — сильный штраф

        g["score"] = 0.5 * freq_norm + 0.3 * avg_sim + 0.1 * hint_match + 0.1 * specificity

    sorted_groups = sorted(groups.values(), key=lambda g: g["score"], reverse=True)
    top_groups = sorted_groups[:max_parameters]

    # Confidence: score нормализованный к theoretical max (1.0)
    # Максимальный score = 0.5*1.0 + 0.3*1.0 + 0.1*1.0 + 0.1*1.3 = 1.03
    theoretical_max = 1.03

    result = []
    for g in top_groups:
        p = g["param"].copy()
        p["confidence"] = round(min(g["score"] / theoretical_max, 1.0), 4)
        p["source"] = "knowledge_base"
        result.append(p)

    logger.info("aggregate: %d кандидатов -> %d параметров", len(candidates), len(result))
    return result


def determine_context(candidates: list) -> dict:
    if not candidates:
        return {"domain": "не определено", "confidence": 0.0}

    domain_scores: dict = {}
    domain_counts: dict = {}
    for c in candidates:
        d = c.get("domain") or "неизвестно"
        domain_scores[d] = domain_scores.get(d, 0.0) + c["similarity"]
        domain_counts[d] = domain_counts.get(d, 0) + 1

    best = max(domain_scores, key=lambda k: domain_scores.get(k, 0.0))
    avg_conf = domain_scores[best] / domain_counts[best]
    return {"domain": best, "confidence": round(avg_conf, 4)}


def detect_ambiguity(
    candidates: list,
    threshold: float,
    delta: float,
) -> dict:
    """Определить, является ли термин неоднозначным по найденным кандидатам.

    Термин считается неоднозначным, если два ведущих домена имеют близкий
    средний similarity (разница не превышает delta) и оба превышают threshold.

    Args:
        candidates: список кандидатов из kb.search_similar_concepts,
                    каждый содержит "domain" и "similarity".
        threshold:  минимальный средний similarity домена (cfg.ambiguity_threshold).
        delta:      максимальная разница similarity между топ-1 и топ-2 доменами
                    (cfg.ambiguity_delta).

    Returns:
        {
            "is_ambiguous": bool,
            "domains":      list[dict],  — домены с их средним score
            "top_domain":   str | None,
            "runner_up":    str | None,
        }
    """
    if not candidates:
        return {
            "is_ambiguous": False,
            "domains": [],
            "top_domain": None,
            "runner_up": None,
        }

    # Собрать суммарный score по доменам
    domain_scores: dict[str, float] = {}
    domain_counts: dict[str, int] = {}
    for c in candidates:
        d = c.get("domain") or "неизвестно"
        domain_scores[d] = domain_scores.get(d, 0.0) + c.get("similarity", 0.0)
        domain_counts[d] = domain_counts.get(d, 0) + 1

    # Средний score по домену
    avg_score: dict[str, float] = {d: domain_scores[d] / domain_counts[d] for d in domain_scores}

    # Сортировка убыванием
    sorted_domains = sorted(avg_score.items(), key=lambda x: x[1], reverse=True)

    domains_list = [{"domain": d, "score": round(s, 4)} for d, s in sorted_domains]

    top_domain = sorted_domains[0][0] if len(sorted_domains) >= 1 else None
    top_score = sorted_domains[0][1] if len(sorted_domains) >= 1 else 0.0
    runner_up = sorted_domains[1][0] if len(sorted_domains) >= 2 else None
    runner_score = sorted_domains[1][1] if len(sorted_domains) >= 2 else 0.0

    is_ambiguous = (
        top_score >= threshold
        and runner_up is not None
        and runner_score >= threshold
        and (top_score - runner_score) <= delta
    )

    logger.debug(
        "ambiguity: is=%s top=%r(%.2f) runner=%r(%.2f)",
        is_ambiguous,
        top_domain,
        top_score,
        runner_up,
        runner_score,
    )

    return {
        "is_ambiguous": is_ambiguous,
        "domains": domains_list,
        "top_domain": top_domain,
        "runner_up": runner_up,
        "domain_candidates": [
            {
                "domain": d,
                "confidence": round(s, 4),
                "example_term": next(
                    (c.get("term") for c in candidates if (c.get("domain") or "неизвестно") == d),
                    None,
                ),
            }
            for d, s in sorted_domains
        ],
    }


def generate_clarification_questions(
    ambiguity_info: dict,
    term: str,
) -> list[str]:
    """Сгенерировать вопросы для уточнения домена при неоднозначном термине.

    Args:
        ambiguity_info: результат detect_ambiguity().
        term:           исходный термин из запроса.

    Returns:
        Список строк-вопросов. Пустой список если термин не неоднозначен.
    """
    if not ambiguity_info.get("is_ambiguous"):
        return []

    top = ambiguity_info.get("top_domain", "")
    runner = ambiguity_info.get("runner_up", "")
    return [
        f"Вы имеете в виду '{term}' в контексте '{top}'?",
        f"Или '{term}' в контексте '{runner}'?",
    ]


# --- Изменение 67: Параметр related_params в aggregate_parameters ---

# Сохраняем оригинальную функцию для совместимости
_aggregate_parameters_original = aggregate_parameters


def _aggregate_parameters_extended(
    candidates: list,
    hints_lemmas: list,
    max_parameters: int,
    related_params: list | None = None,
) -> list:
    """Расширенная агрегация с поддержкой параметров из графа отношений.

    Args:
        candidates:     список кандидатов из поиска.
        hints_lemmas:   леммы подсказок.
        max_parameters: макс. параметров в ответе.
        related_params: параметры из графа отношений (с пониженным весом).

    Returns:
        Список агрегированных параметров.
    """
    if not candidates and not related_params:
        return []

    groups: dict = {}

    # Основные кандидаты
    for candidate in candidates:
        sim = candidate["similarity"]
        for param in candidate.get("parameters", []):
            name = param["name"]
            if name not in groups:
                groups[name] = {
                    "param": param.copy(),
                    "similarities": [],
                    "freq": 0,
                }
            groups[name]["similarities"].append(sim)
            groups[name]["freq"] += 1

    # Параметры из графа отношений (с relation_confidence_mult)
    conf_mult = 0.7
    for rp in (related_params or []):
        name = rp.get("name", "")
        if not name:
            continue
        rp_conf = float(rp.get("confidence", 1.0)) * conf_mult
        if name not in groups:
            groups[name] = {
                "param": rp.copy(),
                "similarities": [],
                "freq": 0,
            }
        groups[name]["similarities"].append(rp_conf)
        groups[name]["freq"] += 1
        # Убрать служебные ключи
        groups[name]["param"].pop("_relation_type", None)
        groups[name]["param"].pop("_source_concept_id", None)

    if not groups:
        return []

    top_sim = max(candidate["similarity"] for candidate in candidates)

    weak_threshold = top_sim * 0.85
    groups = {
        name: g for name, g in groups.items()
        if max(g["similarities"]) >= weak_threshold
    }
    if not groups:
        return []

    max_freq = max(g["freq"] for g in groups.values())
    hint_set = {lemma for sub in hints_lemmas for lemma in sub}

    for g in groups.values():
        freq_norm = g["freq"] / max_freq
        avg_sim = sum(g["similarities"]) / len(g["similarities"])
        hint_match = _compute_hint_match(g["param"], hint_set)
        max_sim = max(g["similarities"])
        if max_sim >= top_sim * 0.95:
            specificity = 1.3
        elif max_sim >= top_sim * 0.85:
            specificity = 1.0
        else:
            specificity = 0.3
        g["score"] = 0.5 * freq_norm + 0.3 * avg_sim + 0.1 * hint_match + 0.1 * specificity

    sorted_groups = sorted(groups.values(), key=lambda g: g["score"], reverse=True)
    top_groups = sorted_groups[:max_parameters]

    max_score = top_groups[0]["score"] if top_groups else 1.0
    if max_score <= 0:
        max_score = 1.0

    result = []
    for g in top_groups:
        p = g["param"].copy()
        p["confidence"] = round(g["score"] / max_score, 4)
        p["source"] = "knowledge_base"
        result.append(p)

    logger.info("aggregate: %d кандидатов -> %d параметров", len(candidates), len(result))
    return result


# --- Изменение 68: Коррекция по обратной связи ---


def apply_feedback_correction(
    candidates: list[dict],
    kb,
    weight: float,
    min_votes: int,
) -> list[dict]:
    """Скорректировать similarity кандидатов на основе обратной связи.

    Понятия с высоким рейтингом получают boost, с низким — penalty.

    Args:
        candidates: список кандидатов (каждый с concept_id и similarity).
        kb:         KnowledgeBase (для get_feedback_stats).
        weight:     вес коррекции (cfg.feedback_weight).
        min_votes:  минимум голосов для применения (cfg.feedback_min_votes).

    Returns:
        Обновлённый список кандидатов.
    """
    if not candidates:
        return candidates

    for c in candidates:
        concept_id = c.get("concept_id")
        if not concept_id:
            continue
        stats = kb.get_feedback_stats(concept_id)
        if stats["votes"] < min_votes:
            continue
        avg = stats["avg_rating"]
        if avg is None:
            continue
        multiplier = 1.0 + (avg - 3.0) * weight
        multiplier = max(0.5, min(multiplier, 1.5))
        c["similarity"] = min(c["similarity"] * multiplier, 1.0)

    candidates.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
    return candidates
