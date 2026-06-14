"""scripts/build_faiss.py -- построение FAISS-индекса из эмбеддингов концептов БД.

Сохраняет FAISS-индекс на диск для дальнейшей загрузки через _load_faiss_index_from_disk.

Требует: pip install faiss-cpu
Использование: python -m scripts.build_faiss
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_FAISS_AVAILABLE = True
try:
    import faiss
except ImportError:
    _FAISS_AVAILABLE = False


def build_faiss_index(config) -> dict:
    """Построить FAISS-индекс из эмбеддингов концептов БД.

    Args:
        config: Config.

    Returns:
        {'index_path': str, 'vectors_count': int} при успехе.
        {'error': str} при ошибке.
    """
    if not _FAISS_AVAILABLE:
        logger.error("faiss-cpu не установлен. pip install faiss-cpu")
        return {"error": "faiss_not_installed"}

    faiss_path_str = getattr(config, "faiss_index_path", "")
    if faiss_path_str:
        output_path = Path(faiss_path_str)
    else:
        output_path = Path(config.db_path).parent / "faiss.index"
        logger.warning("faiss_index_path не задан, сохраняю в: %s", output_path)

    try:
        from src.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(config=config, embedding_model=None, synonym_dict=None)
        concepts = kb.get_all_concepts(use_cache=False)
        kb.close()

        if not concepts:
            logger.error(
                "База концептов пуста. Сначала выполните seed_data или update_kb."
            )
            return {"error": "empty_database"}

        valid = [c for c in concepts if not np.all(c["embedding"] == 0)]
        skipped = len(concepts) - len(valid)
        if skipped:
            logger.warning("Пропущено %d концептов с нулевым эмбеддингом", skipped)
        if not valid:
            logger.error("Нет концептов с ненулевым эмбеддингом. Запустите seed_data.")
            return {"error": "no_valid_embeddings"}

        matrix = np.stack([c["embedding"] for c in valid]).astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.maximum(norms, 1e-9)

        dim = matrix.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        logger.info(
            "FAISS индекс построен: %d векторов, размерность %d", index.ntotal, dim
        )

        id_map_path = output_path.with_suffix(".ids.json")
        id_map = [c["id"] for c in valid]
        id_map_path.write_text(
            json.dumps(id_map, ensure_ascii=False), encoding="utf-8"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(output_path))
        logger.info("Индекс сохранён: %s", output_path)
        logger.info("Маппинг ID сохранён: %s", id_map_path)
        print(f"НАПОМИНАНИЕ: установите в configs/config.json:")
        print(f"  \"use_faiss\": true")
        print(f"  \"faiss_index_path\": \"{output_path}\"")

        return {"index_path": str(output_path), "vectors_count": index.ntotal}

    except Exception as exc:
        logger.error("Ошибка построения FAISS-индекса: %s", exc)
        return {"error": str(exc)}


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.config import Config

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Построить FAISS-индекс")
    parser.add_argument("--config", default="configs/config.json")
    parser.add_argument("--output", default=None, help="Override faiss_index_path")
    args = parser.parse_args()

    try:
        cfg = Config.from_json(args.config, project_root=Path("."))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        cfg.faiss_index_path = args.output

    result = build_faiss_index(cfg)
    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"FAISS индекс готов: {result['vectors_count']} векторов -> {result['index_path']}")
