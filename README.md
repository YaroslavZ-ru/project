# AI-Terminator

Получает термин + подсказки, определяет контекст, возвращает параметры для описания.

```
вход:  термин="ключ"  +  hints=["техника"]
выход: домен="слесарный инструмент",  параметры: material, size_mm, torque_nm...

вход:  термин="ключ"  +  hints=["музыка"]
выход: домен="музыка",  параметры: clef_type, staff_position...
```

---

## Установка

```bash
pip install -r requirements.txt
python setup_project.py
python -m scripts.setup_all
```

## Запуск

```bash
# API
python -m scripts.run_api              # http://127.0.0.1:8000

# CLI
echo '{"term":"ключ","hints":["техника"]}' | python main.py --once

# Docker
docker compose up -d
```

## Запрос

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
  "parameters": [
    {"name": "material", "confidence": 0.91},
    {"name": "size_mm",  "confidence": 0.87}
  ]
}
```

## API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/v1/query` | Анализ термина |
| POST | `/v1/save_concept` | Добавить понятие в БД |
| POST | `/v1/feedback` | Оценить результат (1-5) |
| GET | `/v1/health` | Проверка здоровья |
| GET | `/v1/metrics` | Метрики Prometheus |
| GET | `/docs` | Swagger UI |

## Требования

**Обязательные:** Python 3.10+, pymorphy3, numpy

**Опциональные** (система деградирует без них):

| Пакет | Зачем |
|---|---|
| `fasttext` | Семантический поиск (без него fallback-шаблоны) |
| `fastapi`, `uvicorn` | REST API |
| `faiss-cpu` | Быстрый поиск при >10k понятий |
| `transformers`, `torch` | Генеративное расширение параметров |
| `prometheus_client` | Метрики |

```bash
pip install -e ".[all]"    # всё сразу
pip install -e ".[dev]"    # для разработки
```

## Тесты

```bash
python -m pytest tests/ -v     # 202 теста, 0 падений
```

## Конфигурация

| Файл | Назначение |
|---|---|
| `configs/config.json` | Основной конфиг |
| `configs/development.json` | Override для dev |
| `configs/production.json` | Override для prod |

Запуск с окружением: `python -m scripts.run_api --env production`
