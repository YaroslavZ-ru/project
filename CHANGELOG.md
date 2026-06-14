# Журнал изменений

  Все значимые изменения в проекте фиксируются здесь.
  Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

## [Unreleased]
### Добавлено
- scripts/healthcheck.py -- диагностика всех компонентов
- Логирование в файл: logs/ai_terminator.log с авторотацией (5 МБ, 3 архива)
- Makefile и make.bat -- команды для Linux/macOS и Windows
- .env.example -- шаблон переменных окружения
### Изменено
- .gitignore: расширен с 7 до 40+ строк
- setup_project.py: новый шаг [7/7] -- создание .env.example

## [0.9.0] -- 2026-06-14
### Добавлено (изм. 35-39)
- Обнаружение неоднозначных терминов (detect_ambiguity, ambiguity_threshold)
- Доменные центроиды: build_centroids.py + KnowledgeBase.load_domain_centroids
- Граф отношений: use_relations, update_relations.py
- Поле needs_clarification в ответе пайплайна и API
- +13 тестов для ambiguity, relations, centroids

## [0.8.0] -- 2026-06-14
### Добавлено (изм. 30-34)
- scripts/evaluate.py + data/eval_dataset.json (Precision@5, Context Accuracy)
- scripts/profile.py (профилирование каждого шага пайплайна)
- scripts/build_faiss.py + KnowledgeBase._load_faiss_index_from_disk
- scripts/build_synonyms.py (RuWordNet + встроенный fallback-словарь)
- Финализация requirements.txt и README.md

## [0.7.0] -- 2026-06-14
### Добавлено (изм. 25-29)
- src/metrics.py: MetricsCollector + опциональный Prometheus
- src/api.py: FastAPI REST API (POST /query, GET /health, GET /metrics)
- scripts/run_api.py, scripts/export_kb.py
- Тесты: test_metrics.py, test_api.py, test_pipeline.py (E2E)
### Изменено
- src/config.py: новые поля use_metrics, api_host, api_port

## [0.6.0] -- 2026-06-14
### Добавлено (изм. 20-24)
- src/utils.py: timed, safe_truncate, unique_ordered
- src/generative.py: GenerativeExpander (LLM-расширение, опциональный)
- src/sessions.py: SessionManager (TTL-кэш сессий)
- scripts/update_kb.py, scripts/build_fallback.py
- Тесты: test_generative.py, test_sessions.py
### Изменено
- main.py: run_pipeline + generative expand + session save

## [0.5.0] -- 2026-06-13
### Добавлено (изм. 16-19)
- src/knowledge_base.py: KnowledgeBase (SQLite + FAISS/linear search)
- src/aggregation.py: aggregate_parameters, determine_context
- src/fallback.py: fallback_response, detect_domain
- scripts/init_db.py, scripts/seed_data.py, scripts/setup_all.py
- Тесты: test_knowledge_base.py, test_aggregation.py, test_fallback.py

## [0.4.0] -- 2026-06-12
### Добавлено (изм. 11-15)
- src/embeddings.py: FastTextWrapper (ленивая загрузка, fallback, LRU-кэш)
- src/vectorize.py: vectorize (взвешенная сумма + L2-нормализация)
- src/cache.py: QueryVectorCache
- Тесты: test_embeddings.py, test_vectorize.py, test_cache.py

## [0.3.0] -- 2026-06-12
### Добавлено (изм. 6-10)
- src/lemmatizer.py: Lemmatizer (pymorphy3, LRU-кэш, синглтон)
- src/synonyms.py: SynonymDict
- src/text_cleaner.py: clean_text
- src/preprocess.py: preprocess, preprocess_full
- Тесты: test_lemmatizer.py, test_synonyms.py, test_text_cleaner.py,
          test_preprocess_base.py, test_preprocess_full.py

## [0.2.0] -- 2026-06-12
### Добавлено (изм. 1-5)
- Структура проекта (setup_project.py)
- src/config.py: Config dataclass с валидацией
- configs/config.json: все параметры с дефолтами
- main.py: скелет (parse_input, _init_components, run_pipeline, main)
- Тесты: test_config.py

## [0.1.0] -- 2026-06-12
### Добавлено
- Инициализация репозитория
- .gitignore, README.md (черновик), requirements.txt
