# REST API

Базовый URL: `http://localhost:8000`

Swagger UI: **http://localhost:8000/docs**

## POST /v1/query

Анализ термина и возврат параметров.

```bash
curl -X POST http://localhost:8000/v1/query
  -H "Content-Type: application/json"
  -d '{}
```

## GET /v1/health

Проверка состояния сервиса.

## GET /v1/kb/stats

Статистика БД.

## Аутентификация

Если `api_key_enabled: true` — передайте заголовок `X-API-Key: ваш_ключ`.

## Rate Limiting

Контролируется полем `rate_limit_rpm` в config.json (0 = без ограничений).
HTTP 429 при превышении лимита.
