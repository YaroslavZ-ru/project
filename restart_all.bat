@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   AI-Terminator — Перезапуск (свежий код)
echo ============================================================
echo.

:: Остановка старых процессов
echo Остановка старых процессов...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul
echo OK
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

:: Запуск API (port 8000)
echo Запуск API на port 8000...
start "AI-Terminator API" cmd /c "venv312\Scripts\python.exe -m scripts.run_api"
timeout /t 8 /nobreak >nul

:: Проверка API
curl -s http://127.0.0.1:8000/v1/health >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: API не запустился!
    pause
    exit /b 1
)
echo OK: API доступен
echo.

:: Запуск Web (port 3000)
echo Запуск Web на port 3000...
start "AI-Terminator Web" cmd /c "cd web && node server.js"
timeout /t 2 /nobreak >nul
echo OK
echo.

:: Открытие браузера
start http://localhost:3000

echo ============================================================
echo   Готово! Браузер открыт.
echo   Web:  http://localhost:3000
echo   API:  http://127.0.0.1:8000
echo ============================================================
echo.
echo Для остановки закройте окна "AI-Terminator API" и "AI-Terminator Web"
pause
