import json
import logging
from pathlib import Path
from src.config import Config
from src.lemmatizer import Lemmatizer

logger = logging.getLogger(__name__)


def load_json_config(path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Файл не найден: %s", path)
        return {}
    except json.JSONDecodeError:
        logger.warning("Ошибка JSON: %s", path)
        return {}


def detect_domain(all_lemmas: set, keywords_path) -> str:
    keywords = load_json_config(keywords_path)
    if not keywords:
        return "общее"
    domain_scores: dict = {}
    for domain, kws in keywords.items():
        domain_scores[domain] = sum(
            1 for kw in kws for lemma in all_lemmas if kw in lemma
        )
    if max(domain_scores.values()) == 0:
        return "общее"
    return max(domain_scores, key=domain_scores.get)


def fallback_response(term: str, processed: dict, config: Config) -> dict:
    term_lemmas  = processed.get("term_lemmas", [])
    hints_nested = processed.get("hints_lemmas", [])
    hints_flat   = [l for sub in hints_nested for l in sub]
    all_lemmas   = set(term_lemmas + hints_flat)

    if not all_lemmas:
        lem = Lemmatizer()
        all_lemmas = set(lem.lemmatize_phrase(term))

    domain    = detect_domain(all_lemmas, config.fallback_domain_keywords_path)
    templates = load_json_config(config.domain_templates_path)
    template  = templates.get(domain, templates.get("общее", {}))
    params    = [p.copy() for p in template.get("parameters", [])]

    for p in params:
        p["confidence"] = 0.3
        p["source"]     = "template"

    logger.warning("фаллбэк: '%s' не найден. Домен: '%s'. Шаблонов: %d.", term, domain, len(params))

    return {
        "status": "ok",
        "term":   term,
        "selected_context": {"domain": domain, "confidence": 0.3},
        "parameters": params,
        "suggested_refinements": [],
        "warnings": [
            "Термин не найден в базе знаний. "
            "Параметры предложены на основе шаблона предметной области."
        ],
    }