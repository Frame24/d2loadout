from selenium.webdriver.common.by import By
import pandas as pd
from modules.scraper import get_d2pt_page_table
from modules.config_manager import get_chrome_driver
from scripts.cleanup import save_to_csv

# URL страницы с мета-данными
link_meta = "https://dota2protracker.com/meta"

# Запуск Selenium WebDriver
driver = get_chrome_driver()
driver.implicitly_wait(3)
driver.get(link_meta)
driver.implicitly_wait(10)

print("checking meta...")

# Список позиций и соответствующие XPATH для парсинга
positions = {
    "pos 1": "//div[contains(text(), 'Carry')]",
    "pos 2": "//div[contains(text(), 'Mid')]",
    "pos 3": "//div[contains(text(), 'Off')]",
    "pos 4": "//div[contains(text(), 'Pos 4')]",
    "pos 5": "//div[contains(text(), 'Pos 5')]"
}

dfs = []

# Проход по всем позициям и сбор данных
for position, xpath in positions.items():
    print(f"fetching heroes info for {position}")
    driver.find_element(By.XPATH, xpath).click()
    df = get_d2pt_page_table(driver)
    df["Role"] = position  # Добавляем колонку с ролью
    dfs.append(df)

df_full = pd.concat(dfs, axis=0)

print("Data collection completed.")

# Сохранение данных о героях в facets_data.csv
save_to_csv(df_full, filename="heroes_data.csv")
print("Данные успешно сохранены в heroes_data.csv")
