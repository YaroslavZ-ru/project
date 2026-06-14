# AI-Terminator

Интеллектуальный помощник: по введённому термину и уточняющим словам
генерирует набор параметров для формального описания термина в базе знаний.

## Назначение

AI-Terminator анализирует термины русского языка и возвращает параметры.
Например: `term="ключ"`, `hints=["техника"]` -- система определит контекст
(слесарный инструмент) и предложит параметры: `size_mm`, `material`, `torque_nm`.
Использует FastText-векторы, SQLite и гибкий пайплайн агрегации параметров.

## Быстрый старт

### 1. Клонировать и настроить

```bash
git clone <repo-url>
cd project
python setup_project.py
pip install -r requirements.txt
```

### 2. Скачать FastText модель

```bash
# Скачать cc.ru.300.bin (~8 ГБ) с https://fasttext.cc/docs/en/crawl-vectors.html
# Поместить в models/cc.ru.300.bin
```

### 3. Инициализировать БД

```bash
python -m scripts.setup_all
```

### 4. Запустить

```bash
# CLI:
python main.py --input '{''"term":"ключ","hints":["техника"]}'

# REST API:
pip install fastapi uvicorn httpx
python -m scripts.run_api
```

## Структура проекта

```
project/
├── src/
│   ├── config.py, text_cleaner.py, lemmatizer.py, synonyms.py
│   ├── preprocess.py, embeddings.py, vectorize.py, cache.py
│   ├── knowledge_base.py, aggregation.py, fallback.py, utils.py
│   └── generative.py, sessions.py, metrics.py, api.py  (17 модулей)
├── scripts/
│   ├── init_db.py, seed_data.py, setup_all.py, update_kb.py
│   ├── build_fallback.py, run_api.py, export_kb.py
│   └── evaluate.py, profile.py, build_faiss.py, build_synonyms.py  (11 скриптов)
├── tests/                 -- 17 тестовых файлов
├── configs/config.json, domain_templates.json, domain_keywords.json
├── data/knowledge_base.db, synonyms.json, eval_dataset.json
└── models/cc.ru.300.bin  (скачать отдельно)
```

## Конфигурация

Файл: `configs/config.json`

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| `min_confidence` | float | 0.3 | Порог сходства |
| `max_parameters` | int | 20 | Макс. параметров |
| `max_candidates` | int | 10 | Макс. кандидатов |
| `use_generative` | bool | false | Включить LLM |
| `use_faiss` | bool | false | FAISS-индекс |
| `use_metrics` | bool | false | Prometheus-метрики |
| `api_host` | str | 127.0.0.1 | Хост REST API |
| `api_port` | int | 8000 | Порт REST API |
| `session_ttl_seconds` | int | 1800 | TTL сессии (сек.) |
| `cache_lemma_size` | int | 5000 | Кэш лемм |

## Скрипты

```bash
python -m scripts.setup_all              # заполнение БД
python -m scripts.update_kb --file ...   # импорт JSON/CSV
python -m scripts.evaluate               # Precision@5
python -m scripts.profile                # профилирование
python -m scripts.build_faiss            # FAISS-индекс
python -m scripts.build_synonyms         # словарь синонимов
python -m scripts.export_kb              # экспорт БД
python -m scripts.run_api                # REST API
```

## REST API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/query` | Анализ термина |
| GET | `/health` | Статус сервера |
| GET | `/metrics` | Prometheus/JSON |
| GET | `/kb/stats` | Статистика БД |

```bash
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{}'
```

## Тестирование

```bash
python -m pytest tests/ -v
```

## Требования

- Python 3.10+
- FastText `cc.ru.300.bin` (~8 ГБ, скачать отдельно)
- Опц.: `faiss-cpu`, `fastapi`, `uvicorn`, `prometheus_client`, `ruwordnet`
