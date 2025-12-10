@echo off
echo ==========================================
echo Запуск тестов с Allure отчетом
echo ==========================================
echo.

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Запуск тестов с генерацией Allure результатов
echo Запуск тестов...
python -m pytest tests/ -v --alluredir=allure-results --clean-alluredir

REM Проверка результата
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo Тесты завершены успешно!
    echo ==========================================
) else (
    echo.
    echo ==========================================
    echo Тесты завершены с ошибками
    echo ==========================================
)

echo.
echo Генерация и открытие Allure отчета...

REM Открытие Allure отчета в браузере
allure serve allure-results

pause
