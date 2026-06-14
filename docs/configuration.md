# Конфигурация

Основной файл: `configs/config.json`

| Поле | Тип | Дефолт | Описание |
|---|---|---|---|
| min_confidence | float | 0.3 | Порог схожести |
| max_candidates | int | 20 | Макс. кандидатов |
| rate_limit_rpm | int | 60 | Запросов в минуту (0=без ограничений) |
| api_key_enabled | bool | false | Включить X-API-Key |
| api_key | str | "" | Секретный ключ |
| environment | str | development | development/production/test |
| log_level | str | INFO | DEBUG/INFO/WARNING/ERROR |
| api_host | str | 127.0.0.1 | Адрес API |
| api_port | int | 8000 | Порт API |

## Окружения

dev.json и prod.json переопределяют поля базового конфига.

```bash
python -m scripts.run_api --env production
```

> api_key в prod.json задаётся через переменные окружения или configs/prod.local.json
