@echo off
title AI-Terminator
color 0A
echo.
echo  ============================================
echo   AI-Terminator Web
echo  ============================================
echo.

:: Проверяем backend
echo  Проверяю backend...
curl -s http://127.0.0.1:8000/v1/health >nul 2>&1
if %errorlevel% neq 0 (
    echo  Backend не запущен. Запускаю...
    start "Backend" /min cmd /c "cd /d %~dp0 && venv312\Scripts\python.exe -m scripts.run_api"
    echo  Жду 8 секунд...
    timeout /t 8 /nobreak >nul
)

:: Запускаем веб
echo  Запускаю веб-сервер...
start "Web" cmd /c "cd /d %~dp0\web && node server.js"
timeout /t 2 /nobreak >nul

:: Открываем браузер
echo  Открываю браузер...
start http://localhost:3000

echo.
echo  ============================================
echo   Браузер открылся!
echo   Если нет: http://localhost:3000
echo  ============================================
echo.
echo  Закрой это окно когда закончишь.
echo.
pause
