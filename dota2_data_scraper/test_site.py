from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def test_dota2protracker():
    print("Тестирование сайта dota2protracker.com...")

    try:
        # Настройки Chrome
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")

        # Экспериментальные опции
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

        # Используем webdriver-manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        print("✅ Chrome драйвер успешно запущен!")

        # Тестируем загрузку страницы
        url = "https://dota2protracker.com/meta"
        print(f"Загружаем страницу: {url}")
        driver.get(url)

        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        print(f"✅ Страница загружена: {driver.title}")

        # Проверяем наличие элементов
        try:
            # Ищем элементы с позициями
            positions = ["Carry", "Mid", "Off", "Pos 4", "Pos 5"]
            for pos in positions:
                elements = driver.find_elements(
                    By.XPATH, f"//div[contains(text(), '{pos}')]"
                )
                if elements:
                    print(f"✅ Найден элемент для позиции: {pos}")
                else:
                    print(f"⚠️ Не найден элемент для позиции: {pos}")

            # Проверяем наличие таблицы
            tables = driver.find_elements(By.TAG_NAME, "table")
            if tables:
                print(f"✅ Найдено таблиц: {len(tables)}")
            else:
                print("⚠️ Таблицы не найдены")

        except Exception as e:
            print(f"⚠️ Ошибка при поиске элементов: {e}")

        time.sleep(2)
        driver.quit()
        print("✅ Тест завершен успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    test_dota2protracker()
