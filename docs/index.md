# AI-Terminator

Интеллектуальный помощник: по термину и уточняющим словам генерирует набор параметров.

## Быстрый старт

```bash
git clone <repo> && cd project
pip install -r requirements.txt
python setup_project.py && python -m scripts.setup_all
python -m scripts.run_api
```

## Архитектура пайплайна

```
term + hints
  => [preprocess] лемматизация, синонимы
  => [vectorize]  FastText вектор 300d
  => [search]     KnowledgeBase (SQLite / FAISS)
  => [aggregate]  параметры + контекст
  => [fallback]   если нет кандидатов
  => JSON (status, parameters, selected_context)
```
