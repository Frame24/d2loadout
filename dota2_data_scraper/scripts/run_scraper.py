from selenium.webdriver.common.by import By
import pandas as pd
from modules.scraper import get_d2pt_page_table
from modules.config_manager import get_chrome_driver

link_meta = "https://dota2protracker.com/meta"
driver = get_chrome_driver()
driver.implicitly_wait(3)
driver.get(link_meta)
driver.implicitly_wait(10)

print("checking meta...")

positions = {
    "Carry": "//div[contains(text(), 'Carry')]",
    "Mid": "//div[contains(text(), 'Mid')]",
    "Off": "//div[contains(text(), 'Off')]",
    "Pos 4": "//div[contains(text(), 'Pos 4')]",
    "Pos 5": "//div[contains(text(), 'Pos 5')]"
}

dfs = []

for position, xpath in positions.items():
    print(f"fetching heroes info for {position}")
    driver.find_element(By.XPATH, xpath).click()
    df = get_d2pt_page_table(driver)
    dfs.append(df)

df_full = pd.concat(dfs, axis=0)

print("Data collection completed.")
