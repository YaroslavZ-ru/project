<# 
  AI-Terminator Web — запуск backend + frontend
  Запуск: powershell -ExecutionPolicy Bypass -File start.ps1
#>

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$webDir = Join-Path $projectRoot "web"
$venvPython = Join-Path $projectRoot "venv312\Scripts\python.exe"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  AI-Terminator — Запуск веб-приложения" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# --- Проверка Python backend ---
$backendRunning = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/health" -UseBasicParsing -TimeoutSec 2
    $backendRunning = $true
    Write-Host "[OK] Backend уже работает на :8000" -ForegroundColor Green
} catch {
    Write-Host "[...] Запускаю backend на :8000..." -ForegroundColor Yellow
    Start-Process -NoNewWindow -FilePath $venvPython -ArgumentList "-m","scripts.run_api" -WorkingDirectory $projectRoot
    # Ждём пока поднимется
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/health" -UseBasicParsing -TimeoutSec 2
            $backendRunning = $true
            Write-Host "[OK] Backend запущен" -ForegroundColor Green
            break
        } catch {
            Write-Host "." -NoNewline
        }
    }
    Write-Host ""
}

if (-not $backendRunning) {
    Write-Host "[ERROR] Backend не запустился за 20 секунд" -ForegroundColor Red
    exit 1
}

# --- Запуск Node.js веб-сервера ---
Write-Host "[...] Запускаю веб-сервер на :3000..." -ForegroundColor Yellow

# Проверяем node_modules
if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
    Write-Host "[...] Устанавливаю npm зависимости..." -ForegroundColor Yellow
    Push-Location $webDir
    npm install
    Pop-Location
}

# Запускаем Node.js
$webProc = Start-Process -NoNewWindow -FilePath "node" -ArgumentList "server.js" -WorkingDirectory $webDir -PassThru
Start-Sleep -Seconds 2

try {
    $r = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 3
    Write-Host "[OK] Веб-сервер запущен" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Веб-сервер не отвечает" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Всё запущено!" -ForegroundColor Green
Write-Host "  Веб-интерфейс: http://localhost:3000" -ForegroundColor White
Write-Host "  Backend API:   http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Swagger UI:    http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Откройте в браузере: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Для остановки: закройте это окно или нажмите Ctrl+C" -ForegroundColor Gray

# Держим окно открытым
Write-Host ""
Write-Host "Нажмите Enter для остановки..." -ForegroundColor Gray
Read-Host

# Остановка
Write-Host "Останавливаю веб-сервер..." -ForegroundColor Yellow
Stop-Process -Id $webProc.Id -Force -ErrorAction SilentlyContinue
Write-Host "Готово." -ForegroundColor Green
