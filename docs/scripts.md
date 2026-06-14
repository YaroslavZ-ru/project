# Скрипты

| Скрипт | Назначение | Команда |
|---|---|---|
| setup_all | Инициализация БД | `python -m scripts.setup_all` |
| run_api | REST API | `python -m scripts.run_api [--env production]` |
| healthcheck | Диагностика | `python -m scripts.healthcheck` |
| update_kb | Обновление БД | `python -m scripts.update_kb --file data.json` |
| export_kb | Экспорт БД | `python -m scripts.export_kb --format json` |
| build_fallback | Fallback эмбеддинги | `python -m scripts.build_fallback` |
| build_faiss | FAISS индекс | `python -m scripts.build_faiss` |
| build_synonyms | Словарь синонимов | `python -m scripts.build_synonyms` |
| build_centroids | Центроиды доменов | `python -m scripts.build_centroids` |
| evaluate | Оценка качества | `python -m scripts.evaluate` |
| profile | Профилирование | `python -m scripts.profile` |
| update_relations | Связи концептов | `python -m scripts.update_relations --file rel.json` |
