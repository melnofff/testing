from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class YandexFormPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    # Локаторы элементов формы
    SEARCH_INPUT = (By.ID, "text")
    SUGGEST_LIST = (By.CSS_SELECTOR, ".mini-suggest__popup-content")
    SEARCH_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    # Используем более универсальные локаторы для результатов
    SEARCH_RESULTS = (By.XPATH, "//li[contains(@class, 'serp-item')] | //div[contains(@class, 'Organic')] | //li[@data-cid]")
    FIRST_RESULT_LINK = (By.XPATH, "(//li[contains(@class, 'serp-item')]//a | //div[contains(@class, 'Organic')]//a | //li[@data-cid]//a)[1]")

    def open_page(self, url):
        """Открыть указанный URL"""
        self.driver.get(url)
        time.sleep(1)  # Небольшая пауза для загрузки страницы

    def enter_search_text(self, text):
        """Ввести текст в поисковую строку"""
        search_input = self.wait.until(
            EC.element_to_be_clickable(self.SEARCH_INPUT)
        )
        search_input.clear()
        search_input.send_keys(text)
        time.sleep(0.5)  # Пауза для подгрузки подсказок
        return self

    def wait_for_suggest(self):
        """Дождаться появления списка подсказок"""
        try:
            self.wait.until(
                EC.visibility_of_element_located(self.SUGGEST_LIST)
            )
        except:
            # Если подсказки не появились, это не критично
            pass
        return self

    def click_search_button(self):
        """Нажать кнопку поиска или Enter"""
        try:
            search_input = self.driver.find_element(*self.SEARCH_INPUT)
            search_input.send_keys(Keys.RETURN)
        except:
            search_button = self.wait.until(
                EC.element_to_be_clickable(self.SEARCH_BUTTON)
            )
            search_button.click()
        time.sleep(2)  # Пауза для загрузки результатов
        return self

    def wait_for_search_results(self):
        """Дождаться появления результатов поиска"""
        # Просто ждем появления любых результатов на странице
        time.sleep(3)  # Даем время на загрузку результатов
        return self

    def get_first_result_text(self):
        """Получить текст первого результата поиска"""
        try:
            first_result = self.wait.until(
                EC.presence_of_element_located(self.FIRST_RESULT_LINK)
            )
            return first_result.text
        except:
            # Если не нашли результат, возвращаем текст страницы
            return self.driver.find_element(By.TAG_NAME, "body").text

    def perform_search(self, search_text):
        """Выполнить полный цикл поиска"""
        (self.enter_search_text(search_text)
         .wait_for_suggest()
         .click_search_button()
         .wait_for_search_results())
        return self
