import os
from fake_useragent import UserAgent

# Путь к ChromeDriver (замени на свой, если необходимо)
CHROMEDRIVER_PATH = r"C:\Program Files (x86)\Chromedriver.exe"

# Настройки Selenium ChromeOptions
CHROME_OPTIONS = [
    f"user-agent={UserAgent().random}",
    "--disable-blink-features",
    "--disable-blink-features=AutomationControlled",
    "--disable-extensions",
    "--no-sandbox",
    "--start-maximized",
    "--disable-dev-shm-usage",
    "--incognito",
    "disable-infobars",
    "--headless",
    "window-size=1920x1080",
    "disable-gpu"
]

# Устанавливаем стратегию загрузки страницы
PAGE_LOAD_STRATEGY = 'eager'

# Время ожидания для Selenium (в секундах)
IMPLICIT_WAIT_TIME = 3
EXPLICIT_WAIT_TIME = 10

# URLs для парсинга
D2PT_META_URL = "https://dota2protracker.com/meta"
D2PT_FACETS_URL = "https://dota2protracker.com/facets"
D2PT_HERO_URL_TEMPLATE = "https://dota2protracker.com/hero/{}"

# Пути к файлам конфигурации Steam
STEAM_PATHS = [
    os.path.join(os.getenv('APPDATA'), r"Microsoft\Windows\Start Menu\Programs\Steam\Steam.lnk"),
    r"C:\Program Files\Steam\steam.exe",
    r"C:\Program Files (x86)\Steam\steam.exe"
]
