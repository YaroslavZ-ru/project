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

Создаёт папки `data/`, `models/`, `logs/`, `configs/` и служебные файлы.

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
|   |-- lemmatizer.py             синглтон-лемматизатор (pymorphy3) с LRU-кэшем
|   |-- synonyms.py               словарь синонимов с весами релевантности
|   |-- text_cleaner.py           очистка входных строк перед лемматизацией
|   |-- preprocess.py             полный пайплайн предобработки с весами токенов
|   |-- embeddings.py             обёртка fastText: ленивая загрузка, LRU, fallback
|   |-- vectorize.py              векторизация запроса по формуле ТЗ + L2-нормализация
|   +-- cache.py                  LRU-кэш векторов запросов
|-- configs/
|   +-- config.json               все настройки системы
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
|   +-- test_pipeline_integration.py
|-- data/
|   |-- synonyms.json             словарь синонимов с весами релевантности
|   +-- (.gitkeep)                БД и модель по итогу будут здесь (в git не хранятся)
|-- models/                       fastText-модель (~8 ГБ, в git не хранится)
|-- logs/                         автогенерируемые логи (в git не хранятся)
+-- scripts/                      вспомогательные скрипты
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
    "domain": "не определено",
    "confidence": 0.0
  },
  "parameters": [],
  "suggested_refinements": [],
  "warnings": []
}
```

| Поле | Описание |
|---|---|
| status | ok или error |
| term | Термин из входа |
| selected_context | Определённый домен и его достоверность |
| parameters | Список параметров термина |
| suggested_refinements | Уточняющие вопросы если термин неоднозначен |
| warnings | Предупреждения |

Ответ с `debug: true`:

```json
{
  "status": "ok",
  "term": "ключ",
  "selected_context": { "domain": "не определено", "confidence": 0.0 },
  "parameters": [],
  "suggested_refinements": [],
  "warnings": [],
  "debug_info": {
    "query_vector": [0.123, -0.045, ...],
    "candidates_raw": [],
    "scores_distribution": []
  }
}
```

| Поле debug_info | Описание |
|---|---|
| query_vector | Нормализованный вектор запроса (300 float) |
| candidates_raw | Сырые кандидаты из БД (заполняется после подключения поиска) |
| scores_distribution | Распределение оценок (заполняется после подключения поиска) |

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

Система выполняет полный цикл предобработки (шаг 1 пайплайна) и векторизацию (шаг 2).

**Шаг 1** (работает): очистка текста, лемматизация, расширение синонимами, назначение весов токенам
(0.7 термин, 0.3 подсказки, 0.1 синонимы).

**Шаг 2** (работает): взвешенная сумма векторов fastText + L2-нормализация.
Вектор кэшируется для повторных запросов.
Если fastText недоступна: используется fallback-файл (.npy), а если и его нет: нулевый вектор
+ предупреждение в ответе, статус остаётся `ok`.

**Шаги 3-5** (в разработке): поиск схожих понятий в БД, агрегация параметров, формирование ответа.

59 автотестов, все проходят.