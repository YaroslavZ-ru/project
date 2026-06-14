"""scripts/run_api.py -- запуск uvicorn с src/api.py.

Использование:
    python -m scripts.run_api
    python -m scripts.run_api --host 0.0.0.0 --port 9000
    python -m scripts.run_api --reload
Значения host/port берутся из configs/config.json, если не указаны явно.
"""

import argparse
import logging
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # sys.path только здесь
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.config import Config

    try:
        import uvicorn
    except ImportError:
        print("Ошибка: uvicorn не установлен. Выполните: pip install uvicorn")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="AI-Terminator API: запуск uvicorn с src.api:app",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Адрес для привязки (default: из config.json, api_host)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Порт для привязки (default: из config.json, api_port)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Включить автоперезагрузку (только для разработки)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.json",
        help="Путь к файлу конфигурации",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        choices=["development", "production", "test"],
        help="Окружение: development, production, test (использует configs/{env}.json override)",
    )
    args = parser.parse_args()

    # Загрузка конфига для получения host/port
    project_root = Path(__file__).parent.parent
    try:
        if args.env:
            cfg = Config.for_environment(args.env, project_root=project_root)
        else:
            cfg = Config.from_json(args.config, project_root=project_root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Ошибка при загрузке конфига: {exc}")
        sys.exit(1)

    host = args.host or cfg.api_host
    port = args.port or cfg.api_port

    logger.info("Запуск API на %s:%d (reload=%s)", host, port, args.reload)

    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level="info",
    )
