import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_all(config, force: bool = False) -> None:
    from scripts.init_db import init_db
    from scripts.seed_data import seed
    from src.lemmatizer import Lemmatizer
    from src.synonyms import SynonymDict
    from src.embeddings import FastTextWrapper
    from src.knowledge_base import KnowledgeBase

    init_db(str(config.db_path))
    logger.info("Шаг 1/3: схема создана.")

    seed(config, force=force)
    logger.info("Шаг 2/3: данные вставлены.")

    Lemmatizer(cache_size=config.cache_lemma_size)
    synonym_dict = SynonymDict(config.synonyms_path)
    fallback_path = Path(config.fallback_embeddings_path) if config.fallback_embeddings_path else None
    embedding_model = FastTextWrapper(
        model_path=Path(config.fasttext_model_path),
        fallback_path=fallback_path,
        cache_size=config.word_vector_cache_size,
    )
    with KnowledgeBase(config, embedding_model, synonym_dict) as kb:
        updated = kb.update_all_embeddings()
        logger.info("Шаг 3/3: пересчитано эмбеддингов: %d.", updated)


if __name__ == "__main__":
    _root = Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from src.config import Config
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Полная инициализация системы")
    parser.add_argument("--force",  action="store_true")
    parser.add_argument("--config", default="configs/config.json")
    args = parser.parse_args()
    cfg = Config.from_json(args.config, project_root=_root)
    setup_all(cfg, force=args.force)