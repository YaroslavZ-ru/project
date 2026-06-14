"""scripts/build_synonyms.py -- создание словаря синонимов.

Конвертирует RuWordNet в data/synonyms.json. Без ruwordnet --
создаёт минимальный встроенный словарь.

Использование:
    python -m scripts.build_synonyms --fallback
    python -m scripts.build_synonyms   (если ruwordnet установлен)
"""

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_RUWORDNET_AVAILABLE = True
try:
    import ruwordnet
except ImportError:
    _RUWORDNET_AVAILABLE = False

_FALLBACK_SYNONYMS: dict[str, list[str]] = {
    "ключ": ["отмычка", "инструмент"],
    "болт": ["крепёж", "шуруп"],
    "гайка": ["крепёж", "контргайка"],
    "материал": ["вещество", "субстанция"],
    "размер": ["габарит", "величина"],
    "тип": ["вид", "разновидность", "категория"],
    "форма": ["вид", "конфигурация", "структура"],
    "цвет": ["окраска", "пигмент"],
    "масса": ["вес", "тяжесть"],
    "длина": ["протяжённость", "размер"],
    "ширина": ["размер", "габарит"],
    "высота": ["высотность", "размер"],
    "инструмент": ["прибор", "орудие"],
    "деталь": ["элемент", "составная часть"],
    "узел": ["соединение", "стык"],
    "покрытие": ["оболочка", "поверхность"],
    "прочность": ["надёжность", "стойкость"],
    "топливо": ["топливный материал", "отопление"],
    "давление": ["натиск", "усилие"],
    "мощность": ["сила", "производительность"],
    "скорость": ["быстрота", "скоростной режим"],
}


def build_from_ruwordnet(output_path: Path, lemmatizer, max_synonyms: int = 10) -> dict:
    """Построить словарь синонимов из RuWordNet.

    Args:
        output_path:  путь для сохранения synonyms.json.
        lemmatizer:   Lemmatizer для лемматизации слов.
        max_synonyms: максимум синонимов на слово.

    Returns:
        {words_count, synonyms_avg, saved_to} или {'error': str}.
    """
    if not _RUWORDNET_AVAILABLE:
        logger.error("ruwordnet не установлен. pip install ruwordnet")
        return {"error": "ruwordnet_not_installed"}

    if lemmatizer is None:
        from src.lemmatizer import Lemmatizer

        lemmatizer = Lemmatizer(cache_size=1000)

    try:
        wn = ruwordnet.RuWordNet()
        logger.info("RuWordNet загружен")
    except Exception as exc:
        logger.error("Ошибка загрузки RuWordNet: %s", exc)
        return {"error": str(exc)}

    try:
        synonyms_dict: dict[str, set[str]] = {}

        for synset in wn.synsets():
            try:
                senses = [s.lemma.lower() for s in synset.senses]
            except AttributeError:
                try:
                    senses = [str(s).lower() for s in synset]
                except Exception:
                    continue

            senses_lemmas = []
            for s in senses:
                lem = lemmatizer.lemmatize_word(s)
                if lem:
                    senses_lemmas.append(lem)
            seen = set()
            unique_lemmas = []
            for lm in senses_lemmas:
                if lm not in seen:
                    seen.add(lm)
                    unique_lemmas.append(lm)
            senses_lemmas = unique_lemmas

            for word in senses_lemmas:
                if word not in synonyms_dict:
                    synonyms_dict[word] = set()
                synonyms_dict[word].update(s for s in senses_lemmas if s != word)

        result = {
            w: list(syns)[:max_synonyms] for w, syns in synonyms_dict.items() if syns
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        avg_syns = sum(len(v) for v in result.values()) / max(1, len(result))
        logger.info("Словарь синонимов: %d слов, avg %.1f", len(result), avg_syns)
        return {
            "words_count": len(result),
            "synonyms_avg": round(avg_syns, 2),
            "saved_to": str(output_path),
        }

    except Exception as exc:
        logger.error("Ошибка build_from_ruwordnet: %s", exc)
        return {"error": str(exc)}


def build_minimal_fallback(output_path: Path) -> dict:
    """Создать минимальный встроенный словарь синонимов.

    Используется если ruwordnet недоступен.

    Args:
        output_path: путь для сохранения synonyms.json.

    Returns:
        {words_count, source} или {'error': str}.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(_FALLBACK_SYNONYMS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Минимальный словарь: %d слов -> %s", len(_FALLBACK_SYNONYMS), output_path
        )
        print(
            f"Создан минимальный словарь: {len(_FALLBACK_SYNONYMS)} слов -> {output_path}"
        )
        return {"words_count": len(_FALLBACK_SYNONYMS), "source": "fallback"}
    except Exception as exc:
        logger.error("Ошибка build_minimal_fallback: %s", exc)
        return {"error": str(exc)}


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.config import Config

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Создать словарь синонимов")
    parser.add_argument("--config", default="configs/config.json")
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-synonyms", type=int, default=10)
    parser.add_argument(
        "--fallback", action="store_true", help="Использовать встроенный словарь"
    )
    args = parser.parse_args()

    try:
        cfg = Config.from_json(args.config, project_root=Path("."))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else Path(cfg.synonyms_path)

    if not _RUWORDNET_AVAILABLE or args.fallback:
        if not _RUWORDNET_AVAILABLE:
            logger.warning("ruwordnet не установлен. Создаю минимальный словарь.")
        result = build_minimal_fallback(output_path)
    else:
        from src.lemmatizer import Lemmatizer

        lem = Lemmatizer(cache_size=cfg.cache_lemma_size)
        result = build_from_ruwordnet(output_path, lem, max_synonyms=args.max_synonyms)

    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"Итог: {result}")
