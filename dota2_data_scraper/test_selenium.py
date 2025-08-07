from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time


def test_selenium():
    print("Тестирование Selenium...")

    try:
        # Простые опции без профиля
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Используем webdriver-manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        print("✅ Chrome драйвер успешно запущен!")

        # Тестируем загрузку страницы
        driver.get("https://www.google.com")
        print(f"✅ Страница загружена: {driver.title}")

        time.sleep(2)
        driver.quit()
        print("✅ Тест завершен успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    test_selenium()
