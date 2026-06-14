"""scripts/healthcheck.py -- диагностика всех компонентов проекта.

Проверяет работоспособность каждого компонента и выводит читаемый отчёт.
exit code 0: все критичные компоненты в порядке.
exit code 1: есть ошибки.

Использование: python -m scripts.healthcheck
"""

import argparse
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import sqlite3
import sys

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Результат одной проверки компонента."""

    name: str
    status: str  # OK | WARN | FAIL
    detail: str


def check_config(config_path: Path) -> CheckResult:
    """Проверить загрузку и валидацию configs/config.json."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.config import Config

        cfg = Config.from_json(config_path, project_root=Path("."))
        return CheckResult(
            "config.json",
            "OK",
            f"db_path={cfg.db_path}, min_confidence={cfg.min_confidence}",
        )
    except FileNotFoundError as exc:
        return CheckResult("config.json", "FAIL", str(exc))
    except (ValueError, Exception) as exc:
        return CheckResult("config.json", "FAIL", str(exc))


def check_database(config) -> CheckResult:
    """Проверить доступность и содержимое БД СеSQLite."""
    db_path = Path(config.db_path)
    if not db_path.exists():
        return CheckResult("База знаний (SQLite)", "FAIL", f"Файл БД не найден: {db_path}")
    try:
        conn = sqlite3.connect(str(db_path))
        n = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        conn.close()
        if n == 0:
            return CheckResult(
                "База знаний (SQLite)", "WARN", "БД пустая. Запустите scripts/seed_data"
            )
        return CheckResult("База знаний (SQLite)", "OK", f"{n} концептов в базе")
    except sqlite3.Error as exc:
        return CheckResult("База знаний (SQLite)", "FAIL", str(exc))


def check_fasttext(config) -> CheckResult:
    """Проверить доступность FastText модели."""
    model_path = Path(config.fasttext_model_path)
    if not model_path.exists():
        return CheckResult(
            "FastText модель",
            "WARN",
            f"Модель не найдена: {model_path}. Поиск через fallback.",
        )
    try:
        import numpy as np

        from src.embeddings import FastTextWrapper

        wrapper = FastTextWrapper(model_path=str(model_path), fallback_path=None, cache_size=10)
        vec = wrapper.get_word_vector("тест")
        if not np.all(vec == 0):
            return CheckResult("FastText модель", "OK", f"Загружена, dim={wrapper.get_dimension()}")
        return CheckResult("FastText модель", "WARN", "Модель загружена но вектор нулевой")
    except Exception as exc:
        return CheckResult("FastText модель", "FAIL", str(exc))


def check_fallback_embeddings(config) -> CheckResult:
    """Проверить наличие fallback-эмбеддингов."""
    fb_path_str = getattr(config, "fallback_embeddings_path", "")
    if not fb_path_str:
        return CheckResult(
            "fallback_embeddings", "WARN", "Не задан. Запустите scripts/build_fallback"
        )
    fb_path = Path(fb_path_str)
    if not fb_path.exists():
        return CheckResult(
            "fallback_embeddings",
            "WARN",
            f"fallback_embeddings.npy не найден: {fb_path}. Запустите scripts/build_fallback",
        )
    try:
        import numpy as np

        d = np.load(str(fb_path), allow_pickle=True).item()
        return CheckResult("fallback_embeddings", "OK", f"{len(d)} слов в fallback-словаре")
    except Exception as exc:
        return CheckResult("fallback_embeddings", "FAIL", str(exc))


def check_synonyms(config) -> CheckResult:
    """Проверить synonyms.json."""
    path = Path(config.synonyms_path)
    if not path.exists():
        return CheckResult("synonyms.json", "FAIL", f"Файл не найден: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return CheckResult("synonyms.json", "FAIL", "Неверный формат")
        if len(data) == 0:
            return CheckResult(
                "synonyms.json",
                "WARN",
                "Пустой словарь. Запустите scripts/build_synonyms",
            )
        return CheckResult("synonyms.json", "OK", f"{len(data)} слов")
    except Exception as exc:
        return CheckResult("synonyms.json", "FAIL", str(exc))


def check_domain_templates(config) -> CheckResult:
    """Проверить domain_templates.json и domain_keywords.json."""
    for attr, label in [
        ("domain_templates_path", "domain_templates.json"),
        ("domain_keywords_path", "domain_keywords.json"),
    ]:
        p = Path(getattr(config, attr, "") or "")
        if not p or not p.exists():
            return CheckResult(label, "FAIL", f"Файл не найден: {p}")
    try:
        data = json.loads(Path(config.domain_templates_path).read_text(encoding="utf-8"))
        n = len(data) if isinstance(data, (dict, list)) else 0
        return CheckResult("domain_templates.json", "OK", f"{n} доменов")
    except Exception as exc:
        return CheckResult("domain_templates.json", "FAIL", str(exc))


def check_faiss(config) -> CheckResult:
    """Проверить FAISS-индекс и наличие библиотеки."""
    if not config.use_faiss:
        return CheckResult("FAISS", "OK", "use_faiss=false (не используется)")
    try:
        import faiss  # noqa: F401
    except ImportError:
        return CheckResult("FAISS", "WARN", "use_faiss=true но faiss-cpu не установлен")
    faiss_path_str = getattr(config, "faiss_index_path", "")
    if faiss_path_str and not Path(faiss_path_str).exists():
        return CheckResult(
            "FAISS",
            "WARN",
            f"FAISS индекс не найден: {faiss_path_str}. Запустите build_faiss",
        )
    return CheckResult("FAISS", "OK", "faiss-cpu установлен")


def check_fastapi(config) -> CheckResult:
    """Проверить наличие fastapi и uvicorn."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401

        return CheckResult("FastAPI / uvicorn", "OK", "fastapi + uvicorn установлены")
    except ImportError as exc:
        return CheckResult("FastAPI / uvicorn", "WARN", f"REST API недоступен: {exc}")


def check_prometheus(config) -> CheckResult:
    """Проверить наличие prometheus_client."""
    if not config.use_metrics:
        return CheckResult("Prometheus", "OK", "use_metrics=false (отключено)")
    try:
        import prometheus_client  # noqa: F401

        return CheckResult("Prometheus", "OK", "prometheus_client установлен")
    except ImportError:
        return CheckResult(
            "Prometheus", "WARN", "use_metrics=true но prometheus_client не установлен"
        )


def check_logs_dir() -> CheckResult:
    """Проверить доступность директории logs/."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return CheckResult(
            "Директория logs/",
            "WARN",
            "logs/ не существует. Запустите setup_project.py",
        )
    try:
        tmp = logs_dir / "._hc_tmp_test"
        tmp.touch()
        tmp.unlink()
        return CheckResult("Директория logs/", "OK", "logs/ доступна")
    except Exception:
        return CheckResult("Директория logs/", "FAIL", "logs/ не доступна для записи")


def run_all_checks(config_path: Path) -> list:
    """Запустить все проверки и вернуть список CheckResult."""
    results = []
    cfg_result = check_config(config_path)
    results.append(cfg_result)
    if cfg_result.status == "FAIL":
        return results  # остальные проверки без конфига бессмысленны
    from src.config import Config

    cfg = Config.from_json(config_path, project_root=Path("."))
    results.append(check_database(cfg))
    results.append(check_fasttext(cfg))
    results.append(check_fallback_embeddings(cfg))
    results.append(check_synonyms(cfg))
    results.append(check_domain_templates(cfg))
    results.append(check_faiss(cfg))
    results.append(check_fastapi(cfg))
    results.append(check_prometheus(cfg))
    results.append(check_logs_dir())
    return results


def print_report(results: list) -> bool:
    """Вывести таблицу статусов всех проверок.

    Returns:
        True если нет ошибок (FAIL).
    """
    ICONS = {"OK": "[OK]  ", "WARN": "[WARN]", "FAIL": "[FAIL]"}
    COL1 = 26
    COL2 = 6
    print()
    print(f"{'Компонент':<{COL1}} | {'Статус':<{COL2}} | Детали")
    print("-" * (COL1 + 2) + "|" + "-" * (COL2 + 2) + "|" + "-" * 40)
    for r in results:
        icon = ICONS.get(r.status, r.status)
        print(f"{r.name:<{COL1}} | {icon:<{COL2}} | {r.detail}")
    print()
    print("Легенда: [OK] [WARN] [FAIL]")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_warn = sum(1 for r in results if r.status == "WARN")
    print(f"Итог: Критичных ошибок: {n_fail} | Предупреждений: {n_warn}")
    print()
    return n_fail == 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Диагностика AI-Terminator")
    parser.add_argument("--config", default="configs/config.json", help="Путь к config.json")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Выход 1 если есть предупреждения (WARN = ошибка)",
    )
    args = parser.parse_args()
    results = run_all_checks(Path(args.config))
    ok = print_report(results)
    if args.strict:
        ok = ok and all(r.status != "WARN" for r in results)
    sys.exit(0 if ok else 1)
