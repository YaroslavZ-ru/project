# ============================================================
# AI-Terminator -- Dockerfile (multi-stage build)
# FastText модель НЕ включается в образ -- монтировать через -v ./models:/app/models
# ============================================================

# === Этап 1: зависимости ===
FROM python:3.11-slim AS builder

WORKDIR /build

# Копируем только requirements для кэширования слоя
COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip --no-cache-dir \
    && /opt/venv/bin/pip install -r requirements.txt --no-cache-dir \
    && /opt/venv/bin/pip install fastapi uvicorn httpx --no-cache-dir

# === Этап 2: финальный образ ===
FROM python:3.11-slim AS runtime

LABEL maintainer="AI-Terminator"
LABEL description="AI-Terminator REST API"
LABEL version="0.9.0"

# Непривилегированный пользователь (безопасность)
RUN groupadd -r aiterminator && useradd -r -g aiterminator aiterminator

WORKDIR /app

# Копируем venv из builder
COPY --from=builder /opt/venv /opt/venv

# Копируем исходный код (БЕЗ venv, .git, models/)
COPY src/          ./src/
COPY scripts/      ./scripts/
COPY configs/      ./configs/
COPY main.py       .
COPY setup_project.py .

# Создаём папки и права
RUN mkdir -p data logs models \
    && chown -R aiterminator:aiterminator /app

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Инициализация структуры и БД
RUN python setup_project.py \
    && python -m scripts.setup_all

USER aiterminator

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -m scripts.healthcheck || exit 1

EXPOSE 8000

# FastText модель монтируется через volume:
#   docker run -v /host/models:/app/models ...
VOLUME ["/app/models", "/app/data"]

CMD ["/opt/venv/bin/python", "-m", "scripts.run_api"]
