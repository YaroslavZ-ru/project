# REST API

Базовый URL: `http://localhost:8000`

Swagger UI: **http://localhost:8000/docs**

## POST /v1/query

Анализ термина и возврат параметров.

```bash
curl -X POST http://localhost:8000/v1/query
  -H "Content-Type: application/json"
  -d '{"term":"ключ","hints":["техника"]}'
```

## POST /v1/save_concept

Сохранить новое понятие в базу знаний.

```bash
curl -X POST http://localhost:8000/v1/save_concept \
  -H "Content-Type: application/json" \
  -d '{
    "term": "ключ торцевой",
    "domain": "слесарный инструмент",
    "parameters": [{"name": "size_mm", "label_ru": "Размер (мм)", "type": "float"}],
    "relations": [{"target_term": "ключ", "relation_type": "is_a"}]
  }'
```

Ответ: `{"concept_id": "...", "status": "ok"}`

После сохранения эмбеддинг пересчитывается автоматически.

## POST /v1/feedback

Принять обратную связь по результату поиска (rating 1-5).

```bash
curl -X POST http://localhost:8000/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{"term": "ключ", "rating": 5, "comment": "Отличный результат"}'
```

При `use_feedback_correction: true` рейтинги влияют на будущие результаты.

## GET /v1/health

Проверка состояния сервиса.

## GET /v1/metrics

Метрики сервиса. Включает: requests_total, requests_ok, requests_error, requests_ambiguous, requests_fallback, cache_hits, cache_misses, generative_calls, generative_timeouts, fallback_activations, avg_pipeline_ms.

## GET /v1/kb/stats

Статистика БД.

## Аутентификация

Если `api_key_enabled: true` — передайте заголовок `X-API-Key: ваш_ключ`.

## Rate Limiting

Контролируется полем `rate_limit_rpm` в config.json (0 = без ограничений).
HTTP 429 при превышении лимита.
