import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

@pytest.fixture
def browser():
    # Настройка опций Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless=new")  # Используем новый headless режим
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Скрываем автоматизацию
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Инициализация драйвера без использования webdriver-manager
    try:
        # Попытка использовать ChromeDriverManager
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
    except Exception:
        # Если не получилось, используем системный chromedriver
        driver = webdriver.Chrome(options=chrome_options)

    # Скрываем признаки WebDriver
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    # Неявное ожидание
    driver.implicitly_wait(10)

    yield driver

    # Закрытие браузера после теста
    driver.quit()

@pytest.fixture
def base_url():
    return "https://ya.ru"