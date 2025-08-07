from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import os
import tempfile
import uuid
import subprocess
import time


def get_chrome_driver():
    chrome_options = webdriver.ChromeOptions()

    # Создаем уникальную временную директорию для профиля Chrome
    temp_dir = os.path.join(
        tempfile.gettempdir(), f"chrome_profile_{uuid.uuid4().hex[:8]}"
    )
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")

    # Минимальные опции для стабильной работы
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=0")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")

    # Используем webdriver-manager для автоматической установки chromedriver
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)
