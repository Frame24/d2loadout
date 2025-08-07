from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import logging

logger = logging.getLogger(__name__)


def select_period_8_days(driver):
    """
    Выбирает период "8 days" на странице dota2protracker.com

    Args:
        driver: WebDriver instance

    Returns:
        bool: True если период успешно выбран, False в противном случае
    """
    try:
        logger.info("Выбираем период '8 days'...")

        # Ждем появления селектора периода (4-й селектор с опциями периода)
        wait = WebDriverWait(driver, 10)
        selects = driver.find_elements(By.CSS_SELECTOR, "select")

        # Ищем селектор с опцией "8 days"
        period_select = None
        for select in selects:
            options = select.find_elements(By.TAG_NAME, "option")
            for option in options:
                if option.get_attribute("value") == "8" and "8 days" in option.text:
                    period_select = select
                    break
            if period_select:
                break

        if not period_select:
            raise Exception("Селектор периода не найден")

        # Находим опцию "8 days" и выбираем её
        select = Select(period_select)
        select.select_by_value("8")

        logger.info("Период '8 days' выбран")
        time.sleep(2)  # Даем время на обновление данных
        return True

    except Exception as e:
        logger.error(f"Ошибка при выборе периода: {e}")
        return False
