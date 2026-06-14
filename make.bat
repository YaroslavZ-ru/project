@echo off
IF "%1"==""         GOTO help
IF "%1"=="help"     GOTO help
IF "%1"=="setup"    GOTO setup
IF "%1"=="test"     GOTO test
IF "%1"=="test-fast" GOTO testfast
IF "%1"=="run"      GOTO run
IF "%1"=="api"      GOTO api
IF "%1"=="health"   GOTO health
IF "%1"=="eval"     GOTO eval
IF "%1"=="profile"  GOTO profile
IF "%1"=="build-fallback"   GOTO buildfallback
IF "%1"=="build-faiss"      GOTO buildfaiss
IF "%1"=="build-synonyms"   GOTO buildsynonyms
IF "%1"=="build-centroids"  GOTO buildcentroids
IF "%1"=="export-kb"        GOTO exportkb
IF "%1"=="clean"    GOTO clean
IF "%1"=="lint"     GOTO lint
GOTO unknown

:help
echo.
echo AI-Terminator -- использование: make.bat [цель]
echo Доступные цели:
echo   make.bat setup          -- инициализация проекта
echo   make.bat test           -- запуск всех тестов
echo   make.bat test-fast      -- тесты (остановка на первой ошибке)
echo   make.bat run            -- запуск CLI (пример)
echo   make.bat api            -- запуск REST API
echo   make.bat health         -- диагностика компонентов
echo   make.bat eval           -- оценка качества
echo   make.bat profile        -- профилирование
echo   make.bat clean          -- очистка кэша
echo   make.bat lint           -- проверка синтаксиса
echo   make.bat build-fallback -- сборка fallback-эмбеддингов
echo   make.bat build-faiss    -- сборка FAISS-индекса
echo   make.bat build-synonyms -- сборка синонимов
echo   make.bat build-centroids-- сборка центроидов
echo   make.bat export-kb      -- экспорт БД
echo.
GOTO end

:setup
python setup_project.py
pip install -r requirements.txt
python -m scripts.setup_all
GOTO end

:test
python -m pytest tests/ -v --tb=short
GOTO end

:testfast
python -m pytest tests/ -x --tb=short
GOTO end

:run
python main.py --input "{"term":"ключ","hints":["техника"]}"
GOTO end

:api
python -m scripts.run_api
GOTO end

:health
python -m scripts.healthcheck
GOTO end

:eval
python -m scripts.evaluate
GOTO end

:profile
python -m scripts.profile
GOTO end

:buildfallback
python -m scripts.build_fallback
GOTO end

:buildfaiss
python -m scripts.build_faiss
GOTO end

:buildsynonyms
python -m scripts.build_synonyms --fallback
GOTO end

:buildcentroids
python -m scripts.build_centroids
GOTO end

:exportkb
python -m scripts.export_kb
GOTO end

:clean
FOR /D /R . %%d IN (__pycache__) DO @IF EXIST "%%d" RD /S /Q "%%d"
FOR /D /R . %%d IN (.pytest_cache) DO @IF EXIST "%%d" RD /S /Q "%%d"
IF EXIST logs\*.log DEL /Q logs\*.log
echo Очистка завершена.
GOTO end

:lint
python -m py_compile src/*.py scripts/*.py
GOTO end

:unknown
echo Неизвестная цель: %1. Выполните make.bat help
EXIT /B 1

:docker-build
docker build -t ai-terminator:latest .
GOTO end

:docker-run
docker run -p 8000:8000 -v %CD%/models:/app/models -v %CD%/data:/app/data ai-terminator:latest
GOTO end

:docker-stop
FOR /F "tokens=*" %%i IN ('docker ps -q --filter ancestor=ai-terminator') DO docker stop %%i
GOTO end

:compose-up
docker compose up -d
GOTO end

:compose-down
docker compose down
GOTO end

:compose-dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
GOTO end

:compose-logs
docker compose logs -f api
GOTO end

:pre-commit-install
pip install pre-commit
pre-commit install
echo pre-commit установлен.
GOTO end

:pre-commit-run
pre-commit run --all-files
GOTO end

:docs-serve
mkdocs serve
GOTO end

:docs-build
mkdocs build
GOTO end

:end
EXIT /B 0
