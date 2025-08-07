from modules.config_manager import get_chrome_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def test_config():
    print("Тестирование конфигурации из modules.config_manager...")

    try:
        driver = get_chrome_driver()
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
    test_config()
