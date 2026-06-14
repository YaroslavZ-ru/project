# AI-Terminator

Интеллектуальный помощник: по термину и 1–3 уточняющим словам система определяет контекст
и возвращает набор параметров для формального описания термина.

```
вход:  термин="ключ"  +  hints=["техника", "вращение"]
выход: домен="слесарный инструмент",  параметры: material, size_mm, head_shape...

вход:  термин="ключ"  +  hints=["музыка"]
выход: домен="музыкальная нотация",  параметры: key_type, pitch, symbol...
```

---

## Быстрый старт

```bash
git clone <repo-url>
cd project
pip install -r requirements.txt
python setup_project.py
python -m scripts.setup_all
```

**FastText модель** (необязательно, но улучшает качество):
```bash
# Скачать cc.ru.300.bin (~8 ГБ) с https://fasttext.cc/docs/en/crawl-vectors.html
# Поместить в models/cc.ru.300.bin
# Windows: pip install fasttext-wheel (вместо fasttext)
```

---

## Запуск

```bash
# CLI
python main.py --input '{"term":"ключ","hints":["техника"]}'

# REST API
python -m scripts.run_api          # http://127.0.0.1:8000
python -m scripts.run_api --env production   # с prod.json override

# Docker
docker compose up -d
```

---

## REST API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/v1/query` | Анализ термина |
| GET | `/v1/health` | Готовность сервиса |
| GET | `/v1/kb/stats` | Статистика БД |
| GET | `/docs` | Swagger UI |

Старые пути `/query`, `/health`, `/metrics`, `/kb/stats` работают как алиасы.

```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"term":"ключ","hints":["техника"]}'
```

```json
{
  "status": "ok",
  "term": "ключ",
  "selected_context": {"domain": "слесарный инструмент"},
  "needs_clarification": false,
  "parameters": [
    {"name": "material", "confidence": 0.91},
    {"name": "size_mm",  "confidence": 0.87}
  ]
}
```

Защита: передайте `X-API-Key: ключ` если `api_key_enabled: true` в конфиге.

---

## Окружения

| Файл | Назначение |
|---|---|
| `configs/config.json` | Базовый конфиг |
| `configs/development.json` | Override для разработки |
| `configs/production.json` | Override для продакшна |

```bash
python -m scripts.run_api --env development
python -m scripts.run_api --env production
```

Главные параметры `config.json`: `min_confidence`, `max_candidates`, `rate_limit_rpm`,
`api_key_enabled`, `use_faiss`, `use_generative`, `use_metrics`.

См. [docs/configuration.md](docs/configuration.md) для полной таблицы полей.

---

## Команды

```bash
# Linux / macOS
make setup           # полная инициализация
make test            # все тесты
make api             # REST API (uvicorn)
make health          # диагностика
make docker-build    # сборка Docker-образа
make compose-up      # запуск через docker compose
make docs-serve      # локальная документация
make lint            # ruff + mypy
```

```bat
rem Windows
make.bat setup
make.bat test
make.bat api
make.bat help        # полный список
```

---

## Диагностика

```bash
python -m scripts.healthcheck
```

Проверяет config, SQLite, FastText, fallback, synonyms, FastAPI.
Код выхода: `0` — всё OK, `1` — есть критические ошибки.

---

## Тесты

```bash
python -m pytest tests/ -q       # быстро
python -m pytest tests/ -v       # подробно
```

**137 тестов, 0 падений.** Тесты работают без FastText-модели и без сети.

---

## Требования

**Обязательные:** Python 3.10+, pymorphy3, numpy.

**Опциональные** (система деградирует без них корректно):

| Пакет | Назначение |
|---|---|
| `fasttext` / `fasttext-wheel` | Семантический поиск |
| `fastapi`, `uvicorn`, `httpx` | REST API |
| `faiss-cpu` | FAISS-индекс (>10k концептов) |
| `transformers`, `torch` | Генеративное расширение |
| `prometheus_client` | Метрики |

```bash
# Установить всё сразу
pip install -e ".[all]"
# Только для разработки
pip install -e ".[dev]"
```

---

Документация: `mkdocs serve` или [docs/](docs/)
