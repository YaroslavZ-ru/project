# AI-Terminator

Интеллектуальная система для генерации параметров, характеристик и ограничений для терминов базы знаний.
Принимает термин и уточняющие слова, возвращает JSON со списком параметров для его формального описания.

---

## Требования

- Python 3.10 или выше

---

## Установка

### 1. Клонировать репозиторий

```
git clone https://github.com/your-org/project.git
cd project
```

### 2. Создать структуру папок

```
python setup_project.py
```

### 3. Создать виртуальное окружение

```
python -m venv venv
```

Активация:

```
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat

# Linux / macOS
source venv/bin/activate
```

### 4. Установить зависимости

```
pip install -r requirements.txt
```

> **Важно для Windows:** `fasttext` требует Microsoft C++ Build Tools.
> Скачать: https://visualstudio.microsoft.com/visual-cpp-build-tools/
> После установки: `pip install fasttext-wheel>=0.9.2`

### 5. Инициализировать базу данных

```
python scripts/setup_all.py
```

Создаёт схему SQLite, заполняет понятиями и пересчитывает эмбеддинги.
При перезапуске добавьте флаг `--force`:

```
python scripts/setup_all.py --force
```

---

## Структура проекта

```
project/
|-- main.py                       точка входа: читает JSON, запускает пайплайн, выводит JSON
|-- setup_project.py              создаёт структуру папок на новой машине
|-- requirements.txt              зависимости проекта
|-- src/
|   |-- __init__.py
|   |-- config.py                 загрузка и валидация config.json
|   |-- text_cleaner.py           очистка входных строк перед лемматизацией
|   |-- lemmatizer.py             синглтон-лемматизатор (pymorphy3) с LRU-кэшем
|   |-- synonyms.py               словарь синонимов с весами релевантности
|   |-- preprocess.py             полный пайплайн предобработки с весами токенов
|   |-- embeddings.py             обёртка fastText: ленивая загрузка, LRU, fallback
|   |-- vectorize.py              векторизация запроса по формуле ТЗ + L2-нормализация
|   |-- cache.py                  LRU-кэш векторов запросов
|   |-- knowledge_base.py         доступ к SQLite-базе: поиск, эмбеддинги, FAISS
|   |-- aggregation.py            ранжирование параметров, определение домена
|   +-- fallback.py               фоллбэк на шаблоны при пустом поиске
|-- configs/
|   |-- config.json               все настройки системы
|   |-- domain_keywords.json      ключевые слова доменов для fallback-определения
|   +-- domain_templates.json     шаблоны параметров по доменам
|-- scripts/
|   |-- __init__.py
|   |-- init_db.py                создаёт схему SQLite (идемпотентно)
|   |-- seed_data.py              заполняет БД начальными понятиями
|   +-- setup_all.py              init_db + seed_data + пересчёт эмбеддингов
|-- tests/
|   |-- __init__.py
|   |-- test_config.py
|   |-- test_lemmatizer.py
|   |-- test_synonyms.py
|   |-- test_text_cleaner.py
|   |-- test_preprocess_base.py
|   |-- test_preprocess_full.py
|   |-- test_embeddings.py
|   |-- test_vectorize.py
|   |-- test_cache.py
|   |-- test_pipeline_integration.py
|   |-- test_knowledge_base.py
|   |-- test_aggregation.py
|   +-- test_fallback.py
|-- data/
|   |-- knowledge_base.db        SQLite-база знаний (в git не хранится)
|   +-- synonyms.json             словарь синонимов с весами релевантности
|-- models/                       fastText-модель (~8 ГБ, в git не хранится)
+-- logs/                         автогенерируемые логи (в git не хранятся)
```

---

## Запуск

Через stdin:

```
echo {"term": "ключ"} | python main.py
```

Через аргумент:

```
python main.py --input {"term": "ключ", "hints": ["техника"]}
```

---

## Формат входа

```json
{
  "term": "ключ",
  "hints": ["техника", "вращение"],
  "debug": false,
  "min_confidence": 0.3
}
```

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| term | строка | да | Анализируемый термин |
| hints | список строк | нет | Уточняющие слова. По умолчанию: [] |
| debug | bool | нет | Добавить debug_info в ответ. По умолчанию: false |
| min_confidence | число | нет | Порог поиска 0.0-1.0. По умолчанию: 0.3 |

---

## Формат выхода

Успешный ответ:

```json
{
  "status": "ok",
  "term": "ключ",
  "selected_context": {
    "domain": "слесарный инструмент",
    "confidence": 0.85
  },
  "parameters": [
    {
      "name": "material",
      "label_ru": "Материал",
      "type": "string",
      "description": "Материал изготовления",
      "confidence": 1.0,
      "source": "knowledge_base"
    }
  ],
  "suggested_refinements": [],
  "warnings": []
}
```

| Поле | Описание |
|---|---|
| status | ok или error |
| term | Термин из входа |
| selected_context | Определённый домен и его достоверность |
| parameters | Список параметров с полями name, label_ru, type, description, confidence, source |
| suggested_refinements | Уточняющие вопросы если термин неоднозначен |
| warnings | Предупреждения |

Ответ с `debug: true` дополнительно содержит `debug_info`:

| Поле debug_info | Описание |
|---|---|
| query_vector | Нормализованный вектор запроса (300 float) |
| candidates_raw | Сравненные понятия из БД с оценками сходства |
| scores_distribution | Достоверность каждого параметра в итоговом ответе |

Ответ при ошибке:

```json
{
  "status": "error",
  "message": "Текст ошибки"
}
```

---

## Тесты

```
python -m pytest tests/ -v
```

---

## Текущий статус реализации

Система выполняет полный пайплайн обработки запроса.

**Шаг 1** (работает): очистка, лемматизация, расширение синонимами, веса токенов
(0.7 термин / 0.3 подсказки / 0.1 синонимы).

**Шаг 2** (работает): взвешенная сумма векторов fastText + L2-нормализация, LRU-кэш вектора запроса.
Если fastText недоступна: fallback через .npy-файл, затем нулевый вектор + warning в ответе.

**Шаг 3** (работает): косинусный поиск в SQLite-базе знаний с авторасширением порога до 0.2
при нехватке кандидатов. Опциональный FAISS при более 10 000 понятий.

**Шаг 4** (работает): агрегация параметров по формуле
0.6×freq + 0.3×avg_sim + 0.1×hint_match. Определение домена.
Фоллбэк на шаблоны доменов при пустом поиске (confidence=0.3, source="template").

**Шаг 5** (работает): формирование итогового JSON-ответа.

87 автотестов, все проходят.
