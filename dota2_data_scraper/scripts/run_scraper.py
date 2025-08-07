from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from modules.scraper import get_d2pt_page_table
from modules.config_manager import get_chrome_driver
from scripts.cleanup import save_to_csv
import time

# URL страницы с мета-данными
link_meta = "https://dota2protracker.com/meta"

# Запуск Selenium WebDriver
driver = get_chrome_driver()
driver.implicitly_wait(3)
driver.get(link_meta)
driver.implicitly_wait(10)

print("checking meta...")

# Обработка диалогового окна (cookie consent или реклама)
try:
    # Ждем появления диалогового окна
    wait = WebDriverWait(driver, 5)

    # Пытаемся найти и закрыть диалоговое окно
    dialog_overlay = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "fc-dialog-overlay"))
    )
    print("Найдено диалоговое окно, пытаемся закрыть...")

    # Ищем кнопку закрытия или принятия
    try:
        # Пытаемся найти кнопку "Accept" или "OK"
        accept_button = driver.find_element(
            By.XPATH,
            "//button[contains(text(), 'Accept') or contains(text(), 'OK') or contains(text(), 'Got it')]",
        )
        accept_button.click()
        print("Диалоговое окно закрыто")
    except:
        # Если не нашли кнопку, пытаемся кликнуть по overlay
        driver.execute_script("arguments[0].click();", dialog_overlay)
        print("Диалоговое окно закрыто через JavaScript")

    time.sleep(2)  # Даем время на закрытие диалога

except Exception as e:
    print(f"Диалоговое окно не найдено или уже закрыто: {e}")

# Список позиций и соответствующие XPATH для парсинга
positions = {
    "pos 1": "//div[contains(text(), 'Carry')]",
    "pos 2": "//div[contains(text(), 'Mid')]",
    "pos 3": "//div[contains(text(), 'Off')]",
    "pos 4": "//div[contains(text(), 'Pos 4')]",
    "pos 5": "//div[contains(text(), 'Pos 5')]",
}

dfs = []

# Проход по всем позициям и сбор данных
for position, xpath in positions.items():
    print(f"fetching heroes info for {position}")

    # Ждем появления элемента и кликаем по нему
    wait = WebDriverWait(driver, 10)
    element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))

    # Пытаемся кликнуть разными способами
    try:
        element.click()
    except:
        # Если обычный клик не работает, используем JavaScript
        driver.execute_script("arguments[0].click();", element)

    time.sleep(2)  # Даем время на загрузку данных

    df = get_d2pt_page_table(driver)
    df["Role"] = position  # Добавляем колонку с ролью
    dfs.append(df)

df_full = pd.concat(dfs, axis=0)

print("Data collection completed.")

# Сохранение данных о героях в facets_data.csv
save_to_csv(df_full, filename="heroes_data.csv")
print("Данные успешно сохранены в heroes_data.csv")
