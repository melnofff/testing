# Скрипт для запуска тестов и открытия Allure отчета
# PowerShell версия

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Запуск тестов с Allure отчетом" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Получаем путь к скрипту
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Активация виртуального окружения
Write-Host "Активация виртуального окружения..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Запуск тестов
Write-Host ""
Write-Host "Запуск тестов..." -ForegroundColor Yellow
python -m pytest tests/ -v --alluredir=allure-results --clean-alluredir

# Проверка результата
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "Тесты завершены успешно!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "Тесты завершены с ошибками" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
}

# Открытие Allure отчета
Write-Host ""
Write-Host "Генерация и открытие Allure отчета в браузере..." -ForegroundColor Yellow
Write-Host ""

allure serve allure-results

Write-Host ""
Write-Host "Готово!" -ForegroundColor Green
pause
