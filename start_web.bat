@echo off
title AI-Terminator
color 0A
echo.
echo  ============================================
echo   AI-Terminator Web (свежий код)
echo  ============================================
echo.

:: Остановка старых процессов API (python с scripts.run_api)
echo  Останавливаю старые процессы...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq AI-Terminator API*" >nul 2>&1
taskkill /F /IM python.exe /FI "MODULES eq scripts.run_api*" >nul 2>&1

:: Остановка по портам (надёжный способ)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :3000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

:: Дополнительная остановка node процессов (веб-сервер)
taskkill /F /IM node.exe >nul 2>&1

timeout /t 2 /nobreak >nul
echo  OK
echo.

:: Проверяем venv
if not exist venv312\Scripts\activate.bat (
    echo  ОШИБКА: Запустите setup.bat!
    pause
    exit /b 1
)
call venv312\Scripts\activate.bat

:: Запуск API (всегда свежий)
echo  Запускаю API...
start "AI-Terminator API" /min cmd /c "cd /d %~dp0 && venv312\Scripts\python.exe -m scripts.run_api"
echo  Жду 10 секунд для прогрева модели...
timeout /t 10 /nobreak >nul

:: Проверка API
curl -s http://127.0.0.1:8000/v1/health >nul 2>&1
if %errorlevel% neq 0 (
    echo  ОШИБКА: API не запустился!
    pause
    exit /b 1
)
echo  API: OK
echo.

:: Запуск веб-сервера
echo  Запускаю веб-сервер...
start "AI-Terminator Web" cmd /c "cd /d %~dp0\web && node server.js"
timeout /t 2 /nobreak >nul

:: Открываем браузер
echo  Открываю браузер...
start http://localhost:3000

echo.
echo  ============================================
echo   Готово! Браузер открыт.
echo   Web:  http://localhost:3000
echo   API:  http://127.0.0.1:8000
echo  ============================================
echo.
echo  Закрой это окно когда закончишь.
echo.
pause
