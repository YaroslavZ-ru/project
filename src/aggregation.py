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