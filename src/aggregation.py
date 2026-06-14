import logging
from src.lemmatizer import Lemmatizer

logger = logging.getLogger(__name__)


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
                    "param":        param.copy(),
                    "similarities": [],
                    "freq":         0,
                }
            groups[name]["similarities"].append(sim)
            groups[name]["freq"] += 1

    if not groups:
        return []

    max_freq = max(g["freq"] for g in groups.values())
    hint_set = {lemma for sub in hints_lemmas for lemma in sub}

    for g in groups.values():
        freq_norm  = g["freq"] / max_freq
        avg_sim    = sum(g["similarities"]) / len(g["similarities"])
        hint_match = _compute_hint_match(g["param"], hint_set)
        g["score"] = 0.6 * freq_norm + 0.3 * avg_sim + 0.1 * hint_match

    sorted_groups = sorted(groups.values(), key=lambda g: g["score"], reverse=True)
    top_groups    = sorted_groups[:max_parameters]

    max_score = top_groups[0]["score"] if top_groups else 1.0
    if max_score <= 0:
        max_score = 1.0

    result = []
    for g in top_groups:
        p = g["param"].copy()
        p["confidence"] = round(g["score"] / max_score, 4)
        p["source"]     = "knowledge_base"
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

    best     = max(domain_scores, key=domain_scores.get)
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
    avg_score: dict[str, float] = {
        d: domain_scores[d] / domain_counts[d]
        for d in domain_scores
    }

    # Сортировка убыванием
    sorted_domains = sorted(avg_score.items(), key=lambda x: x[1], reverse=True)

    domains_list = [
        {"domain": d, "score": round(s, 4)}
        for d, s in sorted_domains
    ]

    top_domain   = sorted_domains[0][0] if len(sorted_domains) >= 1 else None
    top_score    = sorted_domains[0][1] if len(sorted_domains) >= 1 else 0.0
    runner_up    = sorted_domains[1][0] if len(sorted_domains) >= 2 else None
    runner_score = sorted_domains[1][1] if len(sorted_domains) >= 2 else 0.0

    is_ambiguous = (
        top_score >= threshold
        and runner_up is not None
        and runner_score >= threshold
        and (top_score - runner_score) <= delta
    )

    logger.debug(
        "ambiguity: is=%s top=%r(%.2f) runner=%r(%.2f)",
        is_ambiguous, top_domain, top_score, runner_up, runner_score,
    )

    return {
        "is_ambiguous": is_ambiguous,
        "domains": domains_list,
        "top_domain": top_domain,
        "runner_up": runner_up,
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

    top    = ambiguity_info.get("top_domain", "")
    runner = ambiguity_info.get("runner_up", "")
    return [
        f"Вы имеете в виду '{term}' в контексте '{top}'?",
        f"Или '{term}' в контексте '{runner}'?",
    ]