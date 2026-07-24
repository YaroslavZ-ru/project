"""scripts/profile.py -- профилирование производительности AI-Terminator.

Замеряет время каждого шага пайплайна на наборе тестовых запросов.

Использование:
    python -m scripts.profile
    python -m scripts.profile --runs 5
"""

import argparse
import json
import logging
from pathlib import Path
import statistics
import time

logger = logging.getLogger(__name__)

TEST_QUERIES: list[dict] = [
    {"term": "ключ", "hints": ["техника"]},
    {"term": "ключ", "hints": ["музыка"]},
    {"term": "болт", "hints": ["крепёж", "металл"]},
    {"term": "гайка", "hints": []},
    {"term": "термин", "hints": ["база знаний"]},
]


def profile_pipeline(
    config,
    components: tuple,
    queries: list[dict],
    n_runs: int = 3,
) -> dict:
    """Профилировать каждый шаг пайплайна.

    Args:
        config:     Config.
        components: результат _init_components.
        queries:    список запросов {term, hints}.
        n_runs:     число прогонов каждого запроса.

    Returns:
        dict имя_шага -> {min_s, max_s, mean_s, calls}.
    """
    from src.aggregation import aggregate_parameters
    from src.fallback import fallback_response
    from src.preprocess import preprocess
    from src.vectorize import vectorize

    n_runs = max(1, n_runs)
    if not queries:
        queries = TEST_QUERIES

    (
        synonym_dict,
        lemmatizer,
        embedding_model,
        vector_cache,
        kb,
        _gen,
        _sess,
    ) = components

    timings: dict[str, list[float]] = {
        "total": [],
        "preprocess": [],
        "vectorize": [],
        "search": [],
        "aggregate_or_fallback": [],
    }

    for query in queries:
        term = query.get("term", "")
        hints = query.get("hints", [])
        for _ in range(n_runs):
            start_total = time.monotonic()

            # ШАГ 1 -- preprocess
            t0 = time.monotonic()
            try:
                processed = preprocess(term, hints, config, synonym_dict, lemmatizer)
            except Exception:
                processed = {}
            timings["preprocess"].append(time.monotonic() - t0)

            # ШАГ 2 -- vectorize (с кэшем)
            t0 = time.monotonic()
            try:
                query_vector = vector_cache.get(term, hints, config)
                if query_vector is None:
                    query_vector = vectorize(processed, embedding_model)
                    vector_cache.put(term, hints, config, query_vector)
            except Exception:
                import numpy as np

                query_vector = np.zeros(300, dtype=np.float32)
            timings["vectorize"].append(time.monotonic() - t0)

            # ШАГ 3 -- search
            t0 = time.monotonic()
            try:
                candidates = kb.search_similar_concepts(
                    query_vector,
                    max_candidates=config.max_candidates,
                )
            except Exception:
                candidates = []
            timings["search"].append(time.monotonic() - t0)

            # ШАГ 4-5 -- aggregate или fallback
            t0 = time.monotonic()
            try:
                if candidates:
                    aggregate_parameters(candidates, [], config.max_parameters)
                else:
                    fallback_response(term, processed, config)
            except Exception:
                pass
            timings["aggregate_or_fallback"].append(time.monotonic() - t0)

            timings["total"].append(time.monotonic() - start_total)

    stats: dict[str, dict] = {}
    for step, times in timings.items():
        if times:
            stats[step] = {
                "min_s": min(times),
                "max_s": max(times),
                "mean_s": statistics.mean(times),
                "calls": len(times),
            }
        else:
            stats[step] = {"min_s": 0.0, "max_s": 0.0, "mean_s": 0.0, "calls": 0}

    return stats


def run_benchmark(config_path: str, n: int = 10) -> dict:
    """Запуск бенчмарка и проверка порогов производительности.

    Args:
        config_path: Путь к config.json.
        n: Количество запросов для усреднения.

    Returns:
        Словарь с результатами и статусом прохождения порогов.
    """
    from main import _init_components, run_pipeline
    from src.config import Config

    cfg = Config.from_json(Path(config_path), project_root=Path(config_path).parent.parent)
    components = _init_components(cfg)

    (
        synonym_dict,
        lemmatizer,
        embedding_model,
        vector_cache,
        kb,
        generative_expander,
        session_manager,
    ) = components

    test_queries = [
        {"term": "ключ", "hints": ["техника"]},
        {"term": "ключ гаечный", "hints": ["инструмент"]},
        {"term": "ключ скрипичный", "hints": ["музыка"]},
        {"term": "bolt", "hints": []},
        {"term": "резистор", "hints": ["электроника", "ток"]},
    ]

    timings: dict[str, list[float]] = {"total_ms": []}

    for _ in range(n):
        for q in test_queries:
            t0 = time.perf_counter()
            run_pipeline(
                term=q["term"],
                hints=q.get("hints", []),
                debug=False,
                min_confidence=None,
                cfg=cfg,
                lemmatizer=lemmatizer,
                synonym_dict=synonym_dict,
                embedding_model=embedding_model,
                vector_cache=vector_cache,
                kb=kb,
                generative_expander=generative_expander,
                session_manager=session_manager,
            )
            total = (time.perf_counter() - t0) * 1000
            timings["total_ms"].append(total)

    stats: dict[str, dict] = {}
    for key, values in timings.items():
        if values:
            sorted_vals = sorted(values)
            stats[key] = {
                "mean_ms": round(sum(values) / len(values), 2),
                "p50_ms": round(sorted_vals[len(sorted_vals) // 2], 2),
                "p95_ms": round(sorted_vals[int(len(sorted_vals) * 0.95)], 2),
                "p99_ms": round(sorted_vals[int(len(sorted_vals) * 0.99)], 2),
            }

    thresholds = {"total_ms": 300}
    checks: dict[str, dict] = {}
    for metric, threshold in thresholds.items():
        if metric in stats:
            passed = stats[metric]["mean_ms"] < threshold
            checks[metric] = {
                "threshold_ms": threshold,
                "actual_ms": stats[metric]["mean_ms"],
                "passed": passed,
            }

    return {
        "stats": stats,
        "checks": checks,
        "all_passed": all(c["passed"] for c in checks.values()),
    }


def print_profile_report(stats: dict, n_queries: int, n_runs: int) -> None:
    """Вывести отчёт профилирования в stdout.

    Args:
        stats:    словарь со статистикой шагов.
        n_queries: количество запросов.
        n_runs:   число прогонов каждого запроса.
    """
    header = f"{'Шаг':<25} | {'Вызовов':>7} | {'Мин (мс)':>8} | {'Ср (мс)':>7} | {'Макс (мс)':>9}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    display_names = {
        "preprocess": "preprocess",
        "vectorize": "vectorize (с кэшем)",
        "search": "search",
        "aggregate_or_fallback": "aggregate_or_fallback",
        "total": "total",
    }
    for step in ["preprocess", "vectorize", "search", "aggregate_or_fallback", "total"]:
        s = stats.get(step, {})
        name = display_names.get(step, step)
        calls = s.get("calls", 0)
        min_ms = s.get("min_s", 0.0) * 1000
        mean_ms = s.get("mean_s", 0.0) * 1000
        max_ms = s.get("max_s", 0.0) * 1000
        print(f"{name:<25} | {calls:>7} | {min_ms:>8.3f} | {mean_ms:>7.3f} | {max_ms:>9.3f}")
    print(sep)
    print("Примечание: vectorize включает кэш -- повторные запросы быстрее.")
    print(f"Запросов: {n_queries}, прогонов каждого: {n_runs}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from main import _init_components
    from src.config import Config

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Профилирование AI-Terminator")
    parser.add_argument("--config", default="configs/config.json")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--queries", default=None, help="JSON-файл с запросами")
    parser.add_argument("--benchmark", action="store_true", help="Запустить бенчмарк производительности")
    parser.add_argument("--n", type=int, default=10, help="Количество итераций для бенчмарка (default: 10)")
    args = parser.parse_args()

    try:
        cfg = Config.from_json(args.config, project_root=Path("."))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        comps = _init_components(cfg)
    except Exception as exc:
        print(f"ERROR: инициализация: {exc}", file=sys.stderr)
        sys.exit(1)

    queries = TEST_QUERIES
    if args.queries:
        try:
            queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(
                "Не удалось загрузить queries из файла: %s. Использую TEST_QUERIES.",
                exc,
            )

    n_runs = max(1, args.runs)

    if args.benchmark:
        result = run_benchmark(args.config, n=args.n)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["all_passed"] else 1)

    stats = profile_pipeline(cfg, comps, queries, n_runs=n_runs)
    print_profile_report(stats, n_queries=len(queries), n_runs=n_runs)
