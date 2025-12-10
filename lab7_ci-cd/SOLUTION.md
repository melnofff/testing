# Решение лабораторной работы №7

## Описание проекта

Автоматизированное тестирование формы поиска Яндекс с использованием CI/CD в GitVerse.

**Технологии:**
- Python 3.11
- Selenium WebDriver
- Pytest
- Allure (отчеты)
- GitHub Actions (в GitVerse)

---

## Возникшие проблемы и их решения

### Проблема 1: CI/CD не запускается автоматически

**Ошибка:**
При загрузке `.gitlab-ci.yml` в GitVerse пайплайн не запускался автоматически.

**Причина:**
GitVerse использует GitHub Actions синтаксис через файл `.gitverse/workflows/python.yaml`, а не GitLab CI через `.gitlab-ci.yml`.

**Решение:**
Создан и настроен файл `.gitverse/workflows/python.yaml` с корректным синтаксисом GitHub Actions.

---

### Проблема 2: Chrome не найден в CI/CD

**Ошибка:**
```
/bin/sh: 1: google-chrome: not found
selenium.common.exceptions.WebDriverException: Service /root/.cache/selenium/chromedriver/linux64/143.0.7499.40/chromedriver unexpectedly exited. Status code was: 127
```

**Причина:**
В CI/CD окружении GitVerse не установлен Google Chrome по умолчанию.

**Решение:**
Добавлен шаг установки Chrome в `.gitverse/workflows/python.yaml`:
```yaml
- name: Install Chrome and ChromeDriver
  run: |
    sudo apt-get update
    sudo apt-get install -y wget unzip
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt-get install -y ./google-chrome-stable_current_amd64.deb
    google-chrome --version
    rm google-chrome-stable_current_amd64.deb
```

---

### Проблема 3: webdriver-manager не может определить версию Chrome

**Ошибка:**
```
AttributeError: 'NoneType' object has no attribute 'split'
```

**Причина:**
`webdriver-manager` пытается автоматически определить версию Chrome, но в CI/CD окружении это не работает.

**Решение:**
Упрощен `conftest.py` - убран `webdriver-manager`, используется только системный Chrome:
```python
# Было:
from webdriver_manager.chrome import ChromeDriverManager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Стало:
driver = webdriver.Chrome(options=chrome_options)
```

---

## Структура проекта

```
lab7_ci-cd/
├── .gitverse/
│   └── workflows/
│       └── python.yaml          # CI/CD конфигурация для GitVerse
├── tests/
│   ├── __init__.py
│   └── test_yandex_form.py      # 5 тестов формы поиска
├── pages/
│   ├── __init__.py
│   └── yandex_form_page.py      # Page Object
├── conftest.py                   # Pytest конфигурация
├── requirements.txt              # Зависимости
├── README.md                     # Документация
└── SOLUTION.md                   # Этот файл
```

---

## Как запустить

### Быстрый запуск (автоматически откроет Allure в браузере):

**Windows (CMD):**
```bash
cd lab7_ci-cd
run_tests.bat
```

**Windows (PowerShell):**
```bash
cd lab7_ci-cd
.\run_tests.ps1
```

### Ручной запуск:

1. **Активировать виртуальное окружение:**
   ```bash
   cd lab7_ci-cd
   venv\Scripts\activate
   ```

2. **Установить зависимости (если не установлены):**
   ```bash
   pip install -r requirements.txt
   ```

3. **Запустить тесты:**
   ```bash
   python -m pytest tests/ -v
   ```

4. **С генерацией Allure отчетов:**
   ```bash
   python -m pytest tests/ -v --alluredir=allure-results
   allure serve allure-results
   ```

> **Примечание:** Команда `allure serve` автоматически откроет отчет в браузере Google Chrome (или браузере по умолчанию)

### В GitVerse:

1. **Проект автоматически запускает CI/CD при каждом push**

2. **Посмотреть результаты:**
   - Откройте проект: https://gitverse.ru/melnoff/lab7_ci-cd
   - Перейдите в раздел **"Actions"**
   - Выберите нужный workflow
   - Посмотрите логи выполнения
   - Скачайте артефакты (allure-results)

3. **Ручной запуск:**
   - Actions → Run workflow → выбрать ветку master → Run

---

## Результаты тестирования

### Локально:
```
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-7.4.3, pluggy-1.6.0
plugins: allure-pytest-2.13.2, xdist-3.5.0
collected 5 items

tests/test_yandex_form.py::TestYandexSearch::test_yandex_search_input[Selenium WebDriver] PASSED [ 20%]
tests/test_yandex_form.py::TestYandexSearch::test_yandex_search_input[Python автоматизация тестирования] PASSED [ 40%]
tests/test_yandex_form.py::TestYandexSearch::test_yandex_search_input[Тестирование программного обеспечения] PASSED [ 60%]
tests/test_yandex_form.py::TestYandexSearch::test_suggest_display PASSED [ 80%]
tests/test_yandex_form.py::TestYandexSearch::test_search_input_clear PASSED [100%]

======================== 5 passed in 77.31s =========================
```

### В CI/CD:
- Workflow запускается автоматически при push
- Устанавливается Chrome
- Запускаются все тесты
- Результаты сохраняются в артефактах

---

## Особенности реализации

### 1. Page Object паттерн
Используется паттерн Page Object для удобного управления элементами страницы:
```python
class YandexFormPage:
    SEARCH_INPUT = (By.ID, "text")

    def enter_search_text(self, text):
        search_input = self.wait.until(
            EC.element_to_be_clickable(self.SEARCH_INPUT)
        )
        search_input.send_keys(text)
```

### 2. Параметризованные тесты
Один тест проверяет несколько вариантов ввода:
```python
@pytest.mark.parametrize("search_query", [
    "Selenium WebDriver",
    "Python автоматизация тестирования",
    "Тестирование программного обеспечения"
])
def test_yandex_search_input(self, browser, base_url, search_query):
    # ...
```

### 3. Headless режим
В CI/CD тесты запускаются в headless режиме (без GUI):
```python
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
```

### 4. Allure отчеты
Используются декораторы Allure для красивых отчетов:
```python
@allure.suite("Тестирование поиска Яндекс")
@allure.title("Тест ввода текста в поисковую строку")
def test_yandex_search_input(self, browser, base_url, search_query):
    with allure.step("Открыть главную страницу Яндекс"):
        # ...
```

---

## Ссылки

- **Проект в GitVerse:** https://gitverse.ru/melnoff/lab7_ci-cd
- **CI/CD Actions:** https://gitverse.ru/melnoff/lab7_ci-cd/actions

---

## Автор

**Автор: Danila Melnikov**

Лабораторная работа №7 по дисциплине "Тестирование программного обеспечения"
