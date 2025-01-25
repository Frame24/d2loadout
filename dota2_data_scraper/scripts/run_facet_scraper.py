from modules.config_manager import get_chrome_driver
from modules.facet_scraper import scrape_facet_data
from scripts.cleanup import save_to_csv

# URL страницы с фасетами
url = "https://dota2protracker.com/facets"

driver = get_chrome_driver()
driver.implicitly_wait(2)
driver.get(url)

df_full_facets = scrape_facet_data(driver)

# Сохранение данных
save_to_csv(df_full_facets, filename="facets_data.csv")
print("Данные успешно сохранены в facets_data.csv")
