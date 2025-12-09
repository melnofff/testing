import pytest
import allure
from pages.yandex_form_page import YandexFormPage
from selenium.webdriver.common.by import By

@allure.suite("Тестирование поиска Яндекс")
class TestYandexSearch:

    @allure.title("Тест ввода текста в поисковую строку")
    @allure.description("Этот тест проверяет возможность ввода текста в поисковую строку")
    @pytest.mark.parametrize("search_query", [
        "Selenium WebDriver",
        "Python автоматизация тестирования",
        "Тестирование программного обеспечения"
    ])
    def test_yandex_search_input(self, browser, base_url, search_query):
        with allure.step(f"Открыть главную страницу Яндекс"):
            form_page = YandexFormPage(browser)
            form_page.open_page(base_url)

        with allure.step(f"Ввести текст в поисковую строку: {search_query}"):
            form_page.enter_search_text(search_query)

        with allure.step("Проверить что текст введен корректно"):
            search_input = browser.find_element(By.ID, "text")
            entered_text = search_input.get_attribute('value')
            assert entered_text == search_query, \
                f"Введенный текст '{entered_text}' не соответствует ожидаемому '{search_query}'"
    
    @allure.title("Тест отображения подсказок при вводе")
    def test_suggest_display(self, browser, base_url):
        with allure.step("Открыть главную страницу Яндекс"):
            form_page = YandexFormPage(browser)
            form_page.open_page(base_url)
        
        with allure.step("Ввести текст в поисковую строку"):
            form_page.enter_search_text("автоматизация тестирования")
        
        with allure.step("Проверить отображение подсказок"):
            # Метод wait_for_suggest выбросит исключение если подсказки не появятся
            form_page.wait_for_suggest()
    
    @allure.title("Тест очистки поисковой строки")
    def test_search_input_clear(self, browser, base_url):
        with allure.step("Открыть главную страницу Яндекс"):
            form_page = YandexFormPage(browser)
            form_page.open_page(base_url)
        
        with allure.step("Ввести текст и очистить поле"):
            form_page.enter_search_text("текст для очистки")
            
            # Получить элемент и очистить его
            search_input = browser.find_element(*form_page.SEARCH_INPUT)
            search_input.clear()
            
            value_after_clear = search_input.get_attribute('value')
        
        with allure.step("Проверить что поле очищено"):
            assert value_after_clear == '', f"Поле не очищено, значение: '{value_after_clear}'"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
