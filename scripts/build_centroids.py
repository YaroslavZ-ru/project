"""scripts/build_centroids.py -- вычисление центроидов доменов.

Для каждого домена вычисляет среднее эмбеддингов концептов (центроид) и сохраняет в JSON.
Центроиды используются для уточнения контекста по истории сессии.

Использование: python -m scripts.build_centroids
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def build_domain_centroids(config) -> dict:
    """Вычислить центроиды доменов из эмбеддингов БД и сохранить в JSON.

    Args:
        config: Config.

    Returns:
        {'saved_path': str, 'domains': list[str], 'min_concepts': int} при успехе.
        {'error': str} при ошибке.
    """
    try:
        from src.knowledge_base import KnowledgeBase
        kb = KnowledgeBase(config=config, embedding_model=None, synonym_dict=None)
        concepts = kb.get_all_concepts(use_cache=False)
        kb.close()
        if not concepts:
            logger.error("База концептов пуста")
            return {"error": "empty_database"}

        groups: dict[str, list[np.ndarray]] = {}
        for c in concepts:
            domain = c.get("domain") or "неизвестно"
            emb = c["embedding"]
            if not np.all(emb == 0):
                groups.setdefault(domain, []).append(emb)

        min_concepts = getattr(config, "domain_centroids_min_concepts", 2)
        centroids: dict[str, list] = {}
        for domain, vecs in groups.items():
            if len(vecs) < min_concepts:
                logger.info("Домен %r: только %d концептов — пропущен", domain, len(vecs))
                continue
            matrix = np.stack(vecs).astype(np.float64)
            centroid = matrix.mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 1e-9:
                centroid = centroid / norm
            centroids[domain] = centroid.tolist()
            logger.info("Центроид домена %r: %d концептов", domain, len(vecs))

        if not centroids:
            logger.error("Нет доменов с достаточным числом концептов (мин %d)", min_concepts)
            return {"error": "no_domains_with_enough_concepts"}

        faiss_path_str = getattr(config, "domain_centroids_path", "")
        if faiss_path_str:
            output_path = Path(faiss_path_str)
        else:
            output_path = Path(config.db_path).parent / "domain_centroids.json"
            logger.warning("домен domain_centroids_path не задан, сохраняю в: %s", output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(centroids, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(">>> Установите в configs/config.json:")
        print(f'>>>   "domain_centroids_path": "{output_path}"')
        return {
            "saved_path": str(output_path),
            "domains": list(centroids.keys()),
            "min_concepts": min_concepts,
        }
    except Exception as exc:
        logger.error("Ошибка build_domain_centroids: %s", exc)
        return {"error": str(exc)}


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.config import Config
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="Вычислить центроиды доменов")
    parser.add_argument("--config", default="configs/config.json")
    parser.add_argument("--output", default=None, help="Override domain_centroids_path")
    args = parser.parse_args()
    try:
        cfg = Config.from_json(args.config, project_root=Path("."))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    if args.output:
        cfg.domain_centroids_path = args.output
    result = build_domain_centroids(cfg)
    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"Центроиды: {result['domains']} -> {result['saved_path']}")
