@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   AI-Terminator — Установка
echo ============================================================
echo.

:: Проверка Python 3.12
echo [1/6] Проверка Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python 3.12 не найден!
    echo.
    echo Скачайте Python 3.12: https://www.python.org/downloads/
    echo При установке отметьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('py -3.12 --version') do set PYVER=%%i
echo OK: %PYVER%
echo.

:: Создание виртуального окружения
echo [2/6] Создание виртуального окружения...
if exist venv312 (
    echo venv312 уже существует, пропускаю...
) else (
    py -3.12 -m venv venv312
    if errorlevel 1 (
        echo ОШИБКА: Не удалось создать venv
        pause
        exit /b 1
    )
)
echo OK
echo.

:: Установка зависимостей
echo [3/6] Установка зависимостей...
call venv312\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
pip install fastapi uvicorn httpx >nul 2>&1
pip install fasttext-wheel >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить fasttext-wheel
    echo Попробуйте: pip install fasttext-wheel
    pause
    exit /b 1
)
echo OK
echo.

:: Скачивание модели FastText
echo [4/6] Скачивание модели FastText (~8 ГБ)...
if exist models\cc.ru.300.bin (
    echo Модель уже существует, пропускаю...
) else (
    echo Скачивание cc.ru.300.bin.gz...
    python -c "import urllib.request; urllib.request.urlretrieve('https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.ru.300.bin.gz', 'models/cc.ru.300.bin.gz')"
    if errorlevel 1 (
        echo ОШИБКА: Не удалось скачать модель
        pause
        exit /b 1
    )
    echo Распаковка...
    python -c "import gzip, shutil; gzip.open('models/cc.ru.300.bin.gz','rb') and shutil.copyfileobj(gzip.open('models/cc.ru.300.bin.gz','rb'), open('models/cc.ru.300.bin','wb'))"
    del models\cc.ru.300.bin.gz
)
echo OK
echo.

:: Инициализация БД
echo [5/6] Инициализация базы данных...
python setup_project.py >nul 2>&1
python -m scripts.setup_all --force >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Не удалось инициализировать БД
    pause
    exit /b 1
)
echo OK
echo.

:: Проверка
echo [6/6] Проверка установки...
python -c "import fasttext; model = fasttext.load_model('models/cc.ru.300.bin'); print('FastText: OK, размерность', model.get_dimension())"
if errorlevel 1 (
    echo ОШИБКА: FastText не загружается
    pause
    exit /b 1
)
echo.

echo ============================================================
echo   Установка завершена успешно!
echo ============================================================
echo.
echo Для запуска: run.bat
echo.
pause
