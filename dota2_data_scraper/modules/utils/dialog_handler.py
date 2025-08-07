"""
Модуль для обработки диалоговых окон на сайте
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

logger = logging.getLogger(__name__)


def handle_dialog_overlay(driver, timeout: int = 5):
    """
    Обработка диалогового окна (cookie consent или реклама)

    Args:
        driver: WebDriver instance
        timeout: Время ожидания появления диалога
    """
    try:
        # Ждем появления диалогового окна
        wait = WebDriverWait(driver, timeout)

        # Пытаемся найти и закрыть диалоговое окно
        dialog_overlay = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "fc-dialog-overlay"))
        )
        logger.info("Найдено диалоговое окно, пытаемся закрыть...")

        # Ищем кнопку закрытия или принятия
        try:
            # Пытаемся найти кнопку "Accept" или "OK"
            accept_button = driver.find_element(
                By.XPATH,
                "//button[contains(text(), 'Accept') or contains(text(), 'OK') or contains(text(), 'Got it')]",
            )
            accept_button.click()
            logger.info("Диалоговое окно закрыто")
        except:
            # Если не нашли кнопку, пытаемся кликнуть по overlay
            driver.execute_script("arguments[0].click();", dialog_overlay)
            logger.info("Диалоговое окно закрыто через JavaScript")

        time.sleep(2)  # Даем время на закрытие диалога

    except Exception as e:
        logger.info(f"Диалоговое окно не найдено или уже закрыто: {e}")
