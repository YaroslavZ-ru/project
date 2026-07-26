@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   AI-Terminator — Запуск
echo ============================================================
echo.

:: Проверка venv
if not exist venv312\Scripts\activate.bat (
    echo ОШИБКА: Виртуальное окружение не найдено!
    echo Сначала запустите: setup.bat
    pause
    exit /b 1
)

:: Активация venv
call venv312\Scripts\activate.bat

:: Проверка модели
if not exist models\cc.ru.300.bin (
    echo ОШИБКА: Модель FastText не найдена!
    echo Сначала запустите: setup.bat
    pause
    exit /b 1
)

echo Выберите режим запуска:
echo.
echo   1. REST API (http://127.0.0.1:8000)
echo   2. CLI (однократный запрос)
echo   3. CLI (интерактивный режим)
echo   4. Веб-интерфейс (http://localhost:3000)
echo   5. Тесты
echo   6. Выход
echo.
set /p CHOICE="Ваш выбор (1-6): "

if "%CHOICE%"=="1" goto api
if "%CHOICE%"=="2" goto cli_once
if "%CHOICE%"=="3" goto cli_loop
if "%CHOICE%"=="4" goto web
if "%CHOICE%"=="5" goto tests
if "%CHOICE%"=="6" goto exit

echo Неверный выбор
pause
goto exit

:api
echo.
echo Запуск API на http://127.0.0.1:8000
echo Для остановки: Ctrl+C
echo.
python -m scripts.run_api
goto exit

:cli_once
echo.
set /p TERM="Введите термин: "
set /p HINTS="Введите подсказки (через запятую): "
echo {"term":"%TERM%","hints":[%HINTS%]} | python main.py --once
pause
goto exit

:cli_loop
echo.
echo Интерактивный режим. Введите JSON или 'exit' для выхода.
echo Пример: {"term":"ключ","hints":["техника"]}
echo.
python main.py
goto exit

:web
echo.
echo Запуск веб-интерфейса...
if not exist web\node_modules (
    echo Устанавливаю npm зависимости...
    cd web
    call npm install
    cd ..
)
echo Открываю браузер...
start http://localhost:3000
start "AI-Terminator Web" cmd /c "cd web && node server.js"
echo.
echo Веб-интерфейс: http://localhost:3000
echo Backend API:   http://127.0.0.1:8000
echo.
echo Для остановки закройте окно "AI-Terminator Web"
pause
goto exit

:tests
echo.
echo Запуск тестов...
python -m pytest tests/ -v --tb=short
pause
goto exit

:exit
deactivate 2>nul
