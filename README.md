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
|-- main.py                  точка входа: читает JSON, запускает пайплайн, выводит JSON
|-- setup_project.py         создает структуру папок на новой машине
|-- requirements.txt         зависимости проекта
|-- src/
|   |-- __init__.py
|   +-- config.py            загрузка и валидация config.json
|-- configs/
|   +-- config.json          все настройки системы
|-- tests/
|   |-- __init__.py
|   +-- test_config.py       автотесты класса Config
|-- data/                    SQLite БД и словари (в git не хранятся)
|-- models/                  предобученная fastText-модель (в git не хранится)
|-- logs/                    автогенерируемые логи (в git не хранятся)
+-- scripts/                 вспомогательные скрипты
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

Система принимает запрос, валидирует вход, загружает конфиг и возвращает правильную структуру JSON.
Пайплайн обработки пока возвращает пустые параметры.
Полноценный анализ терминов будет доступен после подключения модулей лемматизации, векторизации и базы знаний.