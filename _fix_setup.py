#!/usr/bin/env python3
"""setup_project.py -- создаёт полную структуру папок проекта AI-Terminator.

Запускать один раз при развёртывании на новой машине:
    python setup_project.py

Создаёт папки, служебные файлы и .gitignore.
НЕ создаёт БД (это задача scripts/init_db.py).
НЕ устанавливает зависимости (это pip install -r requirements.txt).
"""
from pathlib import Path

ROOT = Path(__file__).parent


def create_dirs() -> list[str]:
    """Создаёт все необходимые директории проекта.

    Returns:
        Список созданных (или уже существующих) путей.
    """
    dirs = [
        ROOT / "src",
        ROOT / "data",
        ROOT / "models",
        ROOT / "tests",
        ROOT / "logs",
        ROOT / "configs",
        ROOT / "scripts",
    ]
    created = []
    for d in dirs:
        existed = d.exists()
        d.mkdir(parents=True, exist_ok=True)
        status = "уже существует" if existed else "создана"
        print(f"  [{status:>16}]  {d.relative_to(ROOT)}")
        created.append(str(d))
    return created


def create_init_files() -> None:
    """Создаёт пустые __init__.py, делающие src/ и tests/ Python-пакетами."""
    init_files = [
        ROOT / "src" / "__init__.py",
        ROOT / "tests" / "__init__.py",
        ROOT / "scripts" / "__init__.py",
    ]
    for f in init_files:
        if not f.exists():
            f.write_text("", encoding="utf-8")
            print(f"  [         создан]  {f.relative_to(ROOT)}")
        else:
            print(f"  [уже существует]  {f.relative_to(ROOT)}")


def create_test_stub() -> None:
    """Создаёт заглушку теста tests/test_config.py."""
    stub = ROOT / "tests" / "test_config.py"
    if not stub.exists():
        stub.write_text(
            "# Тесты для Config будут добавлены в изменении 5\n",
            encoding="utf-8",
        )
        print(f"  [         создан]  {stub.relative_to(ROOT)}")
    else:
        print(f"  [уже существует]  {stub.relative_to(ROOT)}")


def create_main_stub() -> None:
    """Создаёт пустой main.py если его ещё нет."""
    main_py = ROOT / "main.py"
    if not main_py.exists():
        main_py.write_text(
            "# Точка входа AI-Terminator. Реализация — Изменение 3.\n",
            encoding="utf-8",
        )
        print(f"  [         создан]  main.py")
    else:
        print(f"  [уже существует]  main.py")


def create_gitkeep_files() -> None:
    """Добавляет .gitkeep в пустые папки, чтобы Git их отслеживал.

    Git не фиксирует пустые директории. .gitkeep — общепринятое соглашение
    для их сохранения в репозитории.
    """
    # Папки, которые изначально пустые и должны быть видны в GitHub
    empty_dirs = [
        ROOT / "data",
        ROOT / "models",
        ROOT / "logs",
        ROOT / "configs",
    ]
    for d in empty_dirs:
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
            print(f"  [         создан]  {gitkeep.relative_to(ROOT)}")
        else:
            print(f"  [уже существует]  {gitkeep.relative_to(ROOT)}")


def create_gitignore() -> None:
    """Создаёт .gitignore если его ещё нет."""
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        content = (
            "venv/\n"
            "__pycache__/\n"
            "*.pyc\n"
            "logs/*.log\n"
            "models/*.bin\n"
            "data/fallback_embeddings.npy\n"
            ".env\n"
        )
        gitignore.write_text(content, encoding="utf-8")
        print(f"  [         создан]  .gitignore")
    else:
        print(f"  [уже существует]  .gitignore")


def verify_structure() -> bool:
    """Проверяет наличие всех ожидаемых папок и файлов.

    Returns:
        True если всё на месте, False если что-то отсутствует.
    """
    expected = [
        ROOT / "src",
        ROOT / "src" / "__init__.py",
        ROOT / "data",
        ROOT / "models",
        ROOT / "tests",
        ROOT / "tests" / "__init__.py",
        ROOT / "tests" / "test_config.py",
        ROOT / "logs",
        ROOT / "configs",
        ROOT / "scripts",
        ROOT / "scripts" / "__init__.py",
        ROOT / "main.py",
        ROOT / ".gitignore",
        ROOT / "data" / ".gitkeep",
        ROOT / "models" / ".gitkeep",
        ROOT / "logs" / ".gitkeep",
        ROOT / "configs" / ".gitkeep",
    ]
    all_ok = True
    print("\n--- Проверка структуры ---")
    for path in expected:
        if path.exists():
            print(f"  OK: {path.relative_to(ROOT)}")
        else:
            print(f"  ОТСУТСТВУЕТ: {path.relative_to(ROOT)}")
            all_ok = False
    return all_ok


def create_env_example() -> None:
    """Создать .env.example как шаблон переменных окружения."""
    env_example = ROOT / ".env.example"
    if env_example.exists():
        print(f"  [уже существует] .env.example")
        return
    lines = [
        "# AI-Terminator -- пример переменных окружения",
        "# Скопируйте в .env и заполните своими значениями:",
        "#   cp .env.example .env",
        "#",
        "# AI_CONFIG_PATH=configs/config.json",
        "# AI_LOG_LEVEL=INFO",
        "# AI_API_HOST=127.0.0.1",
        "# AI_API_PORT=8000",
    ]
    env_example.write_text(chr(10).join(lines), encoding="utf-8")
    print(f"  [создан] .env.example")


def main() -> None:
    """Точка входа setup_project.py."""
    print("=" * 60)
    print("  AI-Terminator -- создание структуры проекта")
    print("=" * 60)
    print(f"  Корень проекта: {ROOT}\n")

    print("[1/5] Создание директорий...")
    create_dirs()

    print("\n[2/5] Создание __init__.py...")
    create_init_files()

    print("\n[3/5] Создание заглушки теста...")
    create_test_stub()

    print("\n[4/5] Создание main.py...")
    create_main_stub()

    print("\n[5/5] Создание .gitignore...")
    create_gitignore()

    print("\n[6/6] Создание .gitkeep для пустых папок...")
    create_gitkeep_files()
    print("
[7/7] Создание .env.example...")
    create_env_example()

    ok = verify_structure()

    print("\n" + "=" * 60)
    if ok:
        print("  Структура создана успешно!")
        print("\n  Следующие шаги:")
        print("  1. python -m venv venv")
        print("  2. venv\\Scripts\\Activate.ps1  (Windows PowerShell)")
        print("  3. pip install -r requirements.txt")
        print("  4. Скачайте cc.ru.300.bin и поместите в models/")
    else:
        print("  ВНИМАНИЕ: часть элементов структуры отсутствует!")
    print("=" * 60)


if __name__ == "__main__":
    main()
