# AI-Terminator

Интеллектуальный помощник: по термину и подсказкам определяет контекст и возвращает параметры для описания.

```
вход:  термин="ключ"  +  hints=["техника"]
выход: домен="слесарный инструмент",  параметры: material, size_mm, torque_nm...

вход:  термин="ключ"  +  hints=["музыка"]
выход: домен="музыка",  параметры: clef_type, staff_position...
```

---

## Быстрая установка (Windows)

1. Скачайте и установите **Python 3.12**: https://www.python.org/downloads/
   - При установке отметьте **"Add Python to PATH"**

2. Скачайте и установите **Node.js 18+**: https://nodejs.org/
   - При установке отметьте **"Add to PATH"**

3. Скачайте этот репозиторий

4. Запустите **setup.bat** (двойной клик)
   - Установит Python зависимости (~5 мин)
   - Установит Node.js зависимости для веб-приложения
   - Скачает модель FastText (~8 ГБ, ~15 мин)
   - Инициализирует базу данных

5. Запустите **run.bat** (двойной клик)
   - Выберите режим: API, CLI, веб-интерфейс или тесты

---

## Установка вручную

```bash
# 1. Создать виртуальное окружение
py -3.12 -m venv venv312
venv312\Scripts\activate

# 2. Установить зависимости
pip install -r requirements.txt
pip install fastapi uvicorn httpx
pip install fasttext-wheel

# 3. Скачать модель FastText (~8 ГБ)
# Скачать cc.ru.300.bin.gz с https://fasttext.cc/docs/en/crawl-vectors.html
# Распаковать в models/cc.ru.300.bin

# 4. Инициализировать БД
python setup_project.py
python -m scripts.setup_all --force
```

---

## Запуск

```bash
# Активировать окружение
venv312\Scripts\activate

# REST API
python -m scripts.run_api              # http://127.0.0.1:8000

# CLI (один запрос)
echo '{"term":"ключ","hints":["техника"]}' | python main.py --once

# CLI (интерактивный)
python main.py

# Веб-интерфейс (откроется браузер)
start_web.bat                          # http://localhost:3000
```

---

## Запрос к API

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

---

## API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/v1/query` | Анализ термина |
| POST | `/v1/save_concept` | Добавить понятие в БД |
| POST | `/v1/feedback` | Оценить результат (1-5) |
| GET | `/v1/health` | Проверка здоровья |
| GET | `/v1/metrics` | Метрики Prometheus |
| GET | `/docs` | Swagger UI |

---

## Веб-интерфейс

Графический интерфейс для работы с AI-Terminator через браузер.

### Запуск

```bash
# Способ 1: двойной клик
start_web.bat

# Способ 2: вручную
cd web
npm install          # первый раз
npm start            # сервер на http://localhost:3000
```

Скрипт `start_web.bat` автоматически:
- Запускает Python backend (если не работает)
- Запускает Node.js веб-сервер
- Открывает браузер

### Возможности

- **Анализ термина** — вводите термин + подсказки, получаете параметры
- **Выбор домена** — при неоднозначности показываются варианты, клик выбирает домен
- **Экспорт** — скачайте результат в JSON, CSV или TXT
- **Обратная связь** — оцените результат звёздами (1-5)
- **Статистика** — количество понятий и параметров в БД
- **Отладка** — включите чекбокс для вывода debug-информации

### Зависимости

| Пакет | Назначение |
|---|---|
| Node.js >= 18 | JavaScript-րuntime |
| express | Веб-сервер и прокси API |

### Архитектура

```
Браузер (localhost:3000)
    ↓ HTTP
Express.js (web/server.js)  ← проксирует запросы
    ↓ HTTP
FastAPI backend (localhost:8000)
```

Веб-сервер не хранит данные — всё через Python API.

---

## Требования

| Компонент | Минимум | Рекомендуется |
|---|---|---|
| Python | 3.12 | 3.12 |
| Node.js | 18 | 20+ |
| RAM | 4 ГБ | 8 ГБ |
| Диск | 10 ГБ | 20 ГБ |

**Python (обязательные):** pymorphy3, numpy, fasttext-wheel

**Опциональные:**
- `faiss-cpu` — быстрый поиск при >10k понятий
- `transformers`, `torch` — генеративное расширение
- `prometheus_client` — метрики

---

## Тесты

```bash
venv312\Scripts\activate
python -m pytest tests/ -v     # 202 теста, 0 падений
```

---

## Конфигурация

| Файл | Назначение |
|---|---|
| `configs/config.json` | Основной конфиг |
| `configs/development.json` | Override для dev |
| `configs/production.json` | Override для prod |

Запуск с окружением: `python -m scripts.run_api --env production`

---

## Структура проекта

```
project/
├── src/                    # Ядро системы
│   ├── config.py          # Конфигурация
│   ├── preprocess.py      # Предобработка текста
│   ├── embeddings.py      # FastText эмбеддинги
│   ├── vectorize.py       # Векторизация запросов
│   ├── knowledge_base.py  # Поиск в БД
│   ├── aggregation.py     # Агрегация параметров
│   ├── fallback.py        # Резервный режим
│   ├── sessions.py        # Управление сессиями
│   ├── metrics.py         # Метрики Prometheus
│   └── api.py             # REST API
├── web/                   # Веб-интерфейс
│   ├── server.js          # Express-сервер + прокси
│   └── public/            # Статика (HTML, CSS, JS)
├── scripts/               # Утилиты
├── tests/                 # Тесты (229 шт)
├── configs/               # Конфигурация
├── data/                  # БД и данные
├── models/                # Модели (cc.ru.300.bin)
├── setup.bat              # Скрипт установки
├── run.bat                # Скрипт запуска
└── start_web.bat          # Запуск веб-интерфейса
```
