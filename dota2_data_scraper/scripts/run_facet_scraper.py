from modules.config_manager import get_chrome_driver
from modules.facet_scraper import scrape_facet_data
from scripts.cleanup import save_to_csv
from modules.facet_scraper import fetch_facet_data, process_facet_data
from modules.config_manager import get_chrome_driver
from scripts.cleanup import save_to_csv
from modules.period_selector import select_period_8_days
import time

# URL страницы с фасетами
url = "https://dota2protracker.com/facets"

driver = get_chrome_driver()
driver.implicitly_wait(2)
driver.get(url)

# Выбор периода "8 days"
select_period_8_days(driver)

df_full_facets = scrape_facet_data(driver)

# Сохранение основного файла фасетов
save_to_csv(df_full_facets, filename="facets_data.csv")
print("Данные успешно сохранены в facets_data.csv")

# Дополнительный сбор данных по конкретному герою
hero_url = "https://dota2protracker.com/hero/Tiny"
facet_data = fetch_facet_data(hero_url)

if facet_data:
    all_facets_df = process_facet_data(facet_data)
    save_to_csv(all_facets_df, filename="all_facets_data.csv")
    print("Данные успешно сохранены в all_facets_data.csv")
else:
    print("Ошибка: данные фасетов не получены.")
