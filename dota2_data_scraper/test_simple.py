from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
import tempfile
import uuid


def test_simple():
    print("Простой тест Chrome...")

    try:
        # Создаем уникальную временную директорию
        temp_dir = os.path.join(
            tempfile.gettempdir(), f"chrome_test_{uuid.uuid4().hex[:8]}"
        )
        print(f"Используем временную директорию: {temp_dir}")

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-debugging-port=0")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")

        # Используем webdriver-manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        print("✅ Chrome драйвер успешно запущен!")

        # Тестируем загрузку страницы
        driver.get("https://www.google.com")
        print(f"✅ Страница загружена: {driver.title}")

        driver.quit()
        print("✅ Тест завершен успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    test_simple()
