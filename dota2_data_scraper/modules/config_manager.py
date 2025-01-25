from selenium import webdriver
from fake_useragent import UserAgent
import os

def get_chrome_driver():
    chrome_options = webdriver.ChromeOptions()
    
    chrome_options.add_argument("user-agent=" + UserAgent().random)
    chrome_options.add_argument("--disable-blink-features")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("disable-infobars")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--log-level=3")  # Скрытие лишних логов
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-webgl")

    
    chrome_options.add_argument('headless')
    chrome_options.add_argument('window-size=1920x1080')
    chrome_options.add_argument("disable-gpu")
    
    chrome_options.page_load_strategy = 'eager'
    
    os.environ["PATH"] += r"C:\Program Files (x86)\Chromedriver.exe"
    return webdriver.Chrome(options=chrome_options)
