import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

@pytest.fixture
def browser():
    # Настройка опций Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Инициализация драйвера
    # В CI/CD окружении Chrome и ChromeDriver уже установлены
    driver = webdriver.Chrome(options=chrome_options)

    # Скрываем признаки WebDriver
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
    except Exception:
        pass  # Игнорируем ошибки, если CDP недоступен

    # Неявное ожидание
    driver.implicitly_wait(10)

    yield driver

    # Закрытие браузера после теста
    driver.quit()

@pytest.fixture(scope="session")
def base_url():
    return "https://ya.ru"