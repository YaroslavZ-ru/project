"""scripts/evaluate.py -- оценка качества AI-Terminator.

Вычисляет Precision@5 и Context Accuracy на фиксированном эталонном датасете.

Использование:
    python -m scripts.evaluate
    python -m scripts.evaluate --dataset data/eval_dataset.json --json
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Результат оценки одного кейса.

    Attributes:
        id:              идентификатор кейса из датасета.
        term:            анализируемый термин.
        status:          статус ответа пайплайна ("ok" или "error").
        returned_params: имена параметров (name) из ответа.
        returned_domain: домен из selected_context.domain.
        expected_params: ожидаемые имена параметров из датасета.
        expected_domain: ожидаемый домен (None -- не проверяется).
        precision_at_5:  Precision@5 (вычисляется методом).
        domain_correct:  домен совпал с ожидаемым.
        duration_s:      время выполнения в секундах.
    """

    id: str
    term: str
    status: str
    returned_params: list
    returned_domain: str | None
    expected_params: list
    expected_domain: str | None
    precision_at_5: float
    domain_correct: bool
    duration_s: float

    def compute_precision_at_5(self) -> float:
        """Вычислить Precision@5.

        Returns:
            1.0 если expected_params пустой (нет требований).
            Доля попаданий expected_params среди первых 5 возвращённых.
        """
        if not self.expected_params:
            return 1.0
        top5 = self.returned_params[:5]
        hits = len(set(top5) & set(self.expected_params))
        return hits / min(5, len(self.expected_params))

    def compute_domain_correct(self) -> bool:
        """Проверить соответствие домена.

        Returns:
            True если expected_domain is None (не проверяем) или домены совпадают.
        """
        if self.expected_domain is None:
            return True
        return self.returned_domain == self.expected_domain


def run_evaluation(
    dataset_path: Path,
    config,
    components: tuple,
) -> list:
    """Запустить оценку качества на эталонном датасете.

    Args:
        dataset_path: путь к eval_dataset.json.
        config:       Config.
        components:   результат _init_components(config).

    Returns:
        Список EvalResult для каждого кейса датасета.
    """
    from main import run_pipeline

    try:
        raw = dataset_path.read_text(encoding="utf-8")
        cases = json.loads(raw)
    except FileNotFoundError:
        logger.error("Файл датасета не найден: %s", dataset_path)
        return []
    except json.JSONDecodeError as exc:
        logger.error("Ошибка парсинга датасета: %s", exc)
        return []

    if not cases:
        logger.warning("Датасет пустой: %s", dataset_path)
        return []

    (
        synonym_dict,
        lemmatizer,
        embedding_model,
        vector_cache,
        kb,
        generative_expander,
        session_manager,
    ) = components

    results = []
    for case in cases:
        case_id = case.get("id", "unknown")
        term = case.get("term", "")
        hints = case.get("hints", [])
        expected_domain = case.get("expected_domain")
        expected_params = case.get("expected_params", [])

        start = time.monotonic()
        try:
            result = run_pipeline(
                term=term,
                hints=hints,
                debug=False,
                min_confidence=None,
                cfg=config,
                lemmatizer=lemmatizer,
                synonym_dict=synonym_dict,
                embedding_model=embedding_model,
                vector_cache=vector_cache,
                kb=kb,
                generative_expander=generative_expander,
                session_manager=session_manager,
                session_id=None,
            )
            status = result.get("status", "error")
            returned_params = [p["name"] for p in result.get("parameters", [])]
            returned_domain = result.get("selected_context", {}).get("domain")
        except Exception as exc:
            logger.error("Ошибка в кейсе %s: %s", case_id, exc)
            status = "error"
            returned_params = []
            returned_domain = None

        duration = time.monotonic() - start

        er = EvalResult(
            id=case_id,
            term=term,
            status=status,
            returned_params=returned_params,
            returned_domain=returned_domain,
            expected_params=expected_params,
            expected_domain=expected_domain,
            precision_at_5=0.0,
            domain_correct=False,
            duration_s=duration,
        )
        er.precision_at_5 = er.compute_precision_at_5()
        er.domain_correct = er.compute_domain_correct()

        logger.info(
            "eval %s: P@5=%.2f domain=%s t=%.3fs",
            case_id,
            er.precision_at_5,
            er.domain_correct,
            duration,
        )
        results.append(er)

    return results


def compute_summary(results: list) -> dict:
    """Вычислить итоговые метрики оценки.

    Args:
        results: список EvalResult.

    Returns:
        Словарь с precision_at_5, context_accuracy, total_cases и т.д.
    """
    if not results:
        return {
            "precision_at_5": 0.0,
            "context_accuracy": 0.0,
            "total_cases": 0,
            "ok_cases": 0,
            "error_cases": 0,
            "avg_duration_s": 0.0,
        }
    avg_precision = sum(r.precision_at_5 for r in results) / len(results)
    context_accuracy = sum(1 for r in results if r.domain_correct) / len(results)
    avg_dur = sum(r.duration_s for r in results) / len(results)
    return {
        "precision_at_5": round(avg_precision, 4),
        "context_accuracy": round(context_accuracy, 4),
        "total_cases": len(results),
        "ok_cases": len([r for r in results if r.status == "ok"]),
        "error_cases": len([r for r in results if r.status == "error"]),
        "avg_duration_s": round(avg_dur, 4),
    }


def print_report(results: list) -> None:
    """Вывести таблицу результатов оценки в stdout.

    Args:
        results: список EvalResult.
    """
    if not results:
        print("[WARNING] Нет результатов для отображения.")
        return

    header = f"{'ID':<12} | {'Термин':<20} | {'P@5':>4} | {'Домен':>6} | {'Время'}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    for r in results:
        domain_str = "OK" if r.domain_correct else "FAIL"
        term_short = r.term[:18] + ".." if len(r.term) > 20 else r.term
        print(
            f"{r.id:<12} | {term_short:<20} | {r.precision_at_5:>4.2f} | {domain_str:>6} | {r.duration_s:.3f}s"
        )
    print(sep)
    summary = compute_summary(results)
    print(
        f"Precision@5 (avg): {summary['precision_at_5']:.4f} | "
        f"Context Accuracy: {summary['context_accuracy']:.4f} | "
        f"Total: {summary['total_cases']} кейсов"
    )


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.config import Config
    from main import _init_components

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Оценка качества AI-Terminator")
    parser.add_argument(
        "--dataset",
        default="data/eval_dataset.json",
        help="Путь к eval_dataset.json",
    )
    parser.add_argument(
        "--config",
        default="configs/config.json",
        help="Путь к конфигу",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Вывести итог в JSON-формате",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"ERROR: датасет не найден: {dataset_path}", file=sys.stderr)
        sys.exit(1)

    try:
        cfg = Config.from_json(args.config, project_root=Path("."))
    except Exception as exc:
        print(f"ERROR: загрузка конфига: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        components = _init_components(cfg)
    except Exception as exc:
        print(f"ERROR: инициализация компонентов: {exc}", file=sys.stderr)
        sys.exit(1)

    results = run_evaluation(dataset_path, cfg, components)

    if args.json_output:
        summary = compute_summary(results)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_report(results)
        summary = compute_summary(results)
        print()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
