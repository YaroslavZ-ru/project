PYTHON = python

# Цели не являются файлами
.PHONY: help setup test test-fast run api eval profile health
        build-fallback build-faiss build-synonyms build-centroids export-kb clean lint
        docker-build docker-run docker-stop

help:
	@echo ""
	@echo "AI-Terminator -- доступные цели:"
	@echo "  make setup          -- инициализация проекта"
	@echo "  make test           -- запуск всех тестов"
	@echo "  make test-fast      -- тесты, остановиться на первой ошибке"
	@echo "  make run            -- запуск CLI (пример)"
	@echo "  make api            -- запуск REST API"
	@echo "  make health         -- диагностика компонентов"
	@echo "  make eval           -- оценка качества пайплайна"
	@echo "  make docker-build   -- сборка Docker-образа"
	@echo "  make docker-run     -- запуск в Docker на порту 8000"
	@echo "  make docker-stop    -- остановка контейнера"
	@echo "  make profile        -- профилирование производительности"
	@echo "  make build-fallback -- сборка fallback эмбеддингов"
	@echo "  make build-faiss    -- сборка FAISS-индекса"
	@echo "  make build-synonyms -- сборка словаря синонимов"
	@echo "  make build-centroids-- сборка центроидов"
	@echo "  make export-kb      -- экспорт базы знаний"
	@echo "  make clean          -- очистка кэша"
	@echo "  make lint           -- проверка синтаксиса"
	@echo ""

setup:
	$(PYTHON) setup_project.py
	pip install -r requirements.txt
	$(PYTHON) -m scripts.setup_all

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-fast:
	$(PYTHON) -m pytest tests/ -x --tb=short

run:
	$(PYTHON) main.py --input '{"term":"ключ","hints":["техника"]}'

api:
	$(PYTHON) -m scripts.run_api

eval:
	$(PYTHON) -m scripts.evaluate

profile:
	$(PYTHON) -m scripts.profile

health:
	$(PYTHON) -m scripts.healthcheck

build-fallback:
	$(PYTHON) -m scripts.build_fallback

build-faiss:
	$(PYTHON) -m scripts.build_faiss

build-synonyms:
	$(PYTHON) -m scripts.build_synonyms --fallback

build-centroids:
	$(PYTHON) -m scripts.build_centroids

export-kb:
	$(PYTHON) -m scripts.export_kb

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -f logs/*.log

lint:
	$(PYTHON) -m py_compile src/*.py scripts/*.py

docker-build:
	docker build -t ai-terminator:latest .

docker-run:
	docker run -p 8000:8000 \
	    -v $(PWD)/models:/app/models \
	    -v $(PWD)/data:/app/data \
	    ai-terminator:latest

docker-stop:
	docker stop $$(docker ps -q --filter ancestor=ai-terminator) 2>/dev/null || true
