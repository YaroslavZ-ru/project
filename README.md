# AI-Terminator

Интеллектуальное ядро для анализа терминов русского языка. По введённому
термину и 1-3 уточняющим словам система определяет контекст употребления
и возвращает набор параметров для формального описания термина в базе знаний.

**Пример 1:**

```
term  = "ключ"
hints = ["техника", "вращение"]

-> контекст:    слесарный инструмент
-> параметры:   material, size_mm, head_shape, torque_nm, drive_type
```

**Пример 2:**

```
term  = "ключ"
hints = ["музыка"]

-> контекст:    музыкальная нотация
-> параметры:   key_type, pitch, symbol, scope
-> уточнение:   термин неоднозначен, уточните контекст
```

---

## Быстрый старт

### 1. Клонировать и подготовить

```bash
git clone <repo-url>
cd project
python setup_project.py
pip install -r requirements.txt
```

### 2. Скачать FastText модель

```
Скачать cc.ru.300.bin (~8 ГБ):
https://fasttext.cc/docs/en/crawl-vectors.html

Поместить в:  models/cc.ru.300.bin
```

> **Windows:** если `fasttext` не ставится -- используйте `pip install fasttext-wheel`

### 3. Инициализировать базу знаний

```bash
python -m scripts.setup_all
```

### 4. Проверить готовность системы

```bash
python -m scripts.healthcheck
```

### 5. Запустить

```bash
# CLI (Windows):
python main.py --input "{\"term\":\"ключ\",\"hints\":[\"техника\"]}"

# CLI (Linux / macOS):
python main.py --input '{"term":"ключ","hints":["техника"]}'

# REST API:
pip install fastapi uvicorn httpx
python -m scripts.run_api
```

---

## Структура проекта

```
project/
├── main.py                        точка входа (CLI)
├── setup_project.py               создаёт структуру папок (один раз)
├── requirements.txt
├── Makefile                       команды для Linux / macOS
├── make.bat                       команды для Windows
│
├── src/                           16 модулей
│   ├── config.py                  Config dataclass + валидация
│   ├── text_cleaner.py            очистка входного текста
│   ├── lemmatizer.py              лемматизация (pymorphy3, LRU-кэш)
│   ├── synonyms.py                словарь синонимов (synonyms.json)
│   ├── preprocess.py              предобработка термина и подсказок
│   ├── embeddings.py              FastTextWrapper (ленивая загрузка, fallback)
│   ├── vectorize.py               взвешенная векторизация запроса
│   ├── cache.py                   QueryVectorCache (LRU)
│   ├── knowledge_base.py          KnowledgeBase (SQLite + FAISS/numpy)
│   ├── aggregation.py             агрегация параметров, detect_ambiguity
│   ├── fallback.py                резервный ответ при пустой БД
│   ├── generative.py              GenerativeExpander (LLM, опционально)
│   ├── sessions.py                SessionManager (TTL-кэш сессий)
│   ├── metrics.py                 MetricsCollector (Prometheus, опционально)
│   ├── utils.py                   timed, safe_truncate, unique_ordered
│   └── api.py                     FastAPI REST API (опционально)
│
├── scripts/                       14 скриптов
│   ├── init_db.py                 создаёт схему SQLite
│   ├── seed_data.py               загружает начальные данные
│   ├── setup_all.py               init_db + seed_data одной командой
│   ├── update_kb.py               импорт концептов из JSON / CSV
│   ├── build_fallback.py          строит fallback_embeddings.npy
│   ├── build_faiss.py             строит FAISS-индекс
│   ├── build_synonyms.py          конвертирует RuWordNet в synonyms.json
│   ├── build_centroids.py         вычисляет центроиды доменов
│   ├── update_relations.py        импорт отношений между концептами
│   ├── evaluate.py                Precision@5 и Context Accuracy
│   ├── profile.py                 профилирование каждого шага пайплайна
│   ├── export_kb.py               экспорт базы знаний в JSON
│   ├── run_api.py                 запускает uvicorn
│   └── healthcheck.py             диагностика всех компонентов
│
├── tests/                         18 тестовых файлов, 137 тестов
├── configs/
│   ├── config.json
│   ├── domain_templates.json      шаблоны параметров по доменам
│   └── domain_keywords.json       ключевые слова для определения домена
├── data/
│   ├── knowledge_base.db          SQLite (создаётся scripts/init_db.py)
│   ├── synonyms.json              словарь синонимов
│   └── eval_dataset.json          тестовый набор для evaluate.py
├── models/
│   └── cc.ru.300.bin              FastText (скачать отдельно, ~8 ГБ)
└── logs/
    └── ai_terminator.log          создаётся автоматически (ротация 5 МБ)
```

---

## Конфигурация

Файл: `configs/config.json`

### Основные параметры

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| `db_path` | str | `data/knowledge_base.db` | Путь к SQLite-базе |
| `fasttext_model_path` | str | `models/cc.ru.300.bin` | Путь к FastText модели |
| `synonyms_path` | str | `data/synonyms.json` | Словарь синонимов |
| `min_confidence` | float | 0.3 | Минимальное сходство кандидата |
| `max_candidates` | int | 20 | Макс. кандидатов при поиске |
| `max_parameters` | int | 15 | Макс. параметров в ответе |
| `log_level` | str | `INFO` | Уровень логирования |
| `timeout_seconds` | float | 5.0 | Таймаут пайплайна |

### Кэш и предобработка

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| `cache_lemma_size` | int | 1000 | Размер LRU-кэша лемм |
| `word_vector_cache_size` | int | 20000 | Размер LRU-кэша векторов слов |
| `query_cache_size` | int | 100 | Размер кэша векторов запросов |
| `use_synonyms` | bool | true | Расширять запрос синонимами |
| `max_synonyms_per_token` | int | 2 | Макс. синонимов на токен |
| `max_term_length` | int | 100 | Макс. длина термина (символы) |

### FAISS (опционально)

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| `use_faiss` | bool | false | Использовать FAISS вместо numpy |
| `faiss_threshold` | int | 10000 | Мин. концептов для активации FAISS |
| `faiss_index_path` | str | `""` | Путь к файлу индекса |

### Генеративное расширение (опционально)

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| `use_generative` | bool | false | Включить LLM-расширение |
| `generative_model` | str | `sberbank-ai/rugpt3small_...` | HuggingFace модель |
| `min_parameters_for_generative` | int | 5 | Порог запуска LLM |
| `generative_timeout_seconds` | float | 15.0 | Таймаут LLM |

### Сессии

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| `session_ttl_seconds` | int | 1800 | TTL сессии (30 минут) |
| `session_cache_size` | int | 1000 | Макс. активных сессий |
| `auto_save_domain_on_ok` | bool | true | Сохранять домен при успехе |

### Неоднозначность и домены

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| `ambiguity_threshold` | float | 0.7 | Мин. similarity для «сильного» домена |
| `ambiguity_delta` | float | 0.1 | Макс. разница между топ-доменами |
| `domain_centroids_path` | str | `""` | Путь к файлу центроидов |
| `domain_centroid_threshold` | float | 0.3 | Мин. близость к центроиду |
| `use_relations` | bool | false | Расширять поиск через граф отношений |
| `relation_max_depth` | int | 1 | Глубина обхода графа |
| `relation_decay_factor` | float | 0.5 | Затухание веса на каждом уровне |

### REST API и метрики

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| `api_host` | str | `127.0.0.1` | Хост REST API |
| `api_port` | int | 8000 | Порт REST API |
| `use_metrics` | bool | false | Включить Prometheus-метрики |

---

## Скрипты

### Инициализация и данные

```bash
python -m scripts.setup_all                    # создать БД + загрузить данные
python -m scripts.setup_all --force            # то же, но очистить перед вставкой
python -m scripts.update_kb --file data.json   # импорт концептов из JSON
python -m scripts.update_kb --file data.csv    # импорт концептов из CSV
python -m scripts.export_kb                    # экспорт БД в JSON
```

### Сборка индексов и словарей

```bash
python -m scripts.build_synonyms --fallback    # синонимы из RuWordNet
python -m scripts.build_fallback               # fallback_embeddings.npy
python -m scripts.build_faiss                  # FAISS-индекс (нужен faiss-cpu)
python -m scripts.build_centroids              # центроиды доменов
python -m scripts.update_relations             # граф отношений между концептами
```

### Оценка и профилирование

```bash
python -m scripts.evaluate                     # Precision@5 + Context Accuracy
python -m scripts.profile                      # время каждого шага пайплайна
```

### Запуск и диагностика

```bash
python -m scripts.run_api                      # REST API (uvicorn)
python -m scripts.healthcheck                  # диагностика всех компонентов
python -m scripts.healthcheck --strict         # WARN тоже считается ошибкой
```

---

## REST API

Запуск: `python -m scripts.run_api`
По умолчанию: `http://127.0.0.1:8000`

| Метод | Путь | Описание |
|---|---|---|
| POST | `/query` | Анализ термина |
| GET | `/health` | Готовность сервиса |
| GET | `/metrics` | Метрики (Prometheus text или JSON) |
| GET | `/kb/stats` | Статистика базы знаний |

**Пример запроса:**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"term":"ключ","hints":["техника"]}'
```

**Пример ответа:**

```json
{
  "status": "ok",
  "term": "ключ",
  "selected_context": {"domain": "слесарный инструмент", "confidence": 0.82},
  "needs_clarification": false,
  "parameters": [
    {"name": "material", "confidence": 0.91, "source": "knowledge_base"},
    {"name": "size_mm",  "confidence": 0.87, "source": "knowledge_base"}
  ],
  "suggested_refinements": [],
  "warnings": []
}
```

Поле `needs_clarification: true` означает, что термин неоднозначен.
Уточняющие вопросы возвращаются в `suggested_refinements`.

**Сессии:** передайте `session_id` в запросе, чтобы система запомнила
домен между запросами:

```json
{"term":"ключ","hints":["техника"],"session_id":"user-42"}
```

---

## Диагностика

```bash
python -m scripts.healthcheck
```

Выводит таблицу состояния каждого компонента:

```
Компонент                  | Статус | Детали
---------------------------|--------|------------------------------
config.json                | [OK]   | db_path=..., min_confidence=0.3
База знаний (SQLite)       | [OK]   | 150 концептов в базе
FastText модель            | [WARN] | Модель не найдена. Поиск через fallback.
fallback_embeddings        | [OK]   | 3200 слов в fallback-словаре
synonyms.json              | [OK]   | 45000 слов
domain_templates.json      | [OK]   | 12 доменов
FAISS                      | [OK]   | use_faiss=false (не используется)
FastAPI / uvicorn          | [OK]   | fastapi + uvicorn установлены
Prometheus                 | [OK]   | use_metrics=false (отключено)
Директория logs/           | [OK]   | logs/ доступна
```

Коды выхода: `0` -- всё в порядке, `1` -- есть критические ошибки.
Флаг `--strict` считает предупреждения (`WARN`) ошибками.

---

## Удобные команды

### Windows

```bat
make.bat help            -- список всех команд
make.bat setup           -- полная инициализация проекта
make.bat test            -- запустить все тесты
make.bat health          -- диагностика компонентов
make.bat run             -- пример запуска CLI
make.bat api             -- запустить REST API
make.bat clean           -- удалить кэш и временные файлы
make.bat lint            -- проверка синтаксиса всех модулей
```

### Linux / macOS

```bash
make help
make setup
make test
make health
make run
make api
make clean
make lint
```

---

## Тестирование

```bash
python -m pytest tests/ -v --tb=short    # все тесты с деталями
python -m pytest tests/ -x               # остановиться на первой ошибке
```

Текущее состояние: **137 тестов, 0 падений.**

---

## Требования

**Обязательные:**

```
Python 3.10+
pymorphy3>=2.0.0
pymorphy3-dicts-ru>=2.4.0
numpy>=1.24.0
fasttext>=0.9.2          (Windows: pip install fasttext-wheel)
pytest>=7.0.0
```

**Опциональные:**

```
faiss-cpu>=1.7.0           при use_faiss=true
transformers>=4.30.0       при use_generative=true
torch>=2.0.0               при use_generative=true
fastapi>=0.100.0           REST API
uvicorn>=0.23.0            REST API
httpx>=0.24.0              тесты API
prometheus_client>=0.17.0  при use_metrics=true
ruwordnet                  для scripts/build_synonyms.py
```

Все опциональные зависимости деградируют корректно: система работает
без них, используя numpy-поиск и fallback-эмбеддинги.
