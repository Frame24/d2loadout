"""
Основной класс для управления процессом скрапинга данных Dota 2
"""

import logging
from typing import Optional, Dict, Any
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import tempfile
import uuid
import os

from ..utils.period_selector import select_period_8_days
from ..utils.dialog_handler import handle_dialog_overlay


class ScrapingManager:
    """
    Основной класс для управления процессом скрапинга
    """

    def __init__(self, headless: bool = True, minimize_window: bool = False):
        """
        Инициализация менеджера скрапинга

        Args:
            headless: Запускать браузер в headless режиме
            minimize_window: Минимизировать окно браузера (работает только если headless=False)
        """
        self.headless = headless
        self.minimize_window = minimize_window
        self.driver: Optional[Chrome] = None
        self.logger = self._setup_logging()
        # Регистрируем аварийное закрытие драйвера на случай внезапного завершения процесса
        try:
            import atexit

            atexit.register(self._cleanup_at_exit)
        except Exception:
            pass

    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        return logging.getLogger(__name__)

    def _create_chrome_options(self) -> Options:
        """Создание настроек Chrome"""
        chrome_options = Options()

        # Используем уникальный порт и профиль для каждого экземпляра
        import random
        import tempfile
        import uuid

        port = random.randint(9000, 9999)
        unique_profile = os.path.join(
            tempfile.gettempdir(), f"chrome_profile_{uuid.uuid4().hex[:8]}"
        )

        # Базовые опции для стабильной работы
        if self.headless:
            chrome_options.add_argument("--headless")
        else:
            # Если не headless, но нужно скрыть окно - перемещаем за пределы экрана
            if self.minimize_window:
                chrome_options.add_argument("--window-position=-32000,-32000")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument(f"--remote-debugging-port={port}")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument(f"--user-data-dir={unique_profile}")

        # Экспериментальные опции
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("detach", False)

        chrome_options.page_load_strategy = "eager"

        return chrome_options

    def start_driver(self) -> Chrome:
        """Запуск Chrome драйвера"""
        try:
            self.logger.info("Запуск Chrome драйвера...")

            chrome_options = self._create_chrome_options()
            service = Service(ChromeDriverManager().install())
            self.driver = Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(3)
            
            # Дополнительные способы скрытия окна (если не headless)
            if not self.headless and self.minimize_window:
                try:
                    # Ждем немного, чтобы окно появилось
                    import time
                    time.sleep(0.5)
                    
                    # Используем только Selenium API - он работает с конкретным окном драйвера
                    # Это минимизирует ТОЛЬКО окно нашего драйвера, не трогая другие окна Chrome
                    try:
                        # Selenium 4+ поддерживает minimize_window для текущего окна драйвера
                        self.driver.minimize_window()
                        self.logger.debug("Окно драйвера минимизировано через Selenium API")
                    except AttributeError:
                        # Если метод не поддерживается (старая версия Selenium), 
                        # перемещаем окно за пределы экрана через аргумент Chrome
                        # (это уже сделано в _create_chrome_options через --window-position)
                        self.logger.debug("minimize_window не поддерживается, используется --window-position")
                    except Exception as e:
                        self.logger.debug(f"Не удалось минимизировать окно через Selenium: {e}")
                except Exception as e:
                    self.logger.debug(f"Не удалось скрыть окно: {e}")
            
            self.logger.info("Chrome драйвер успешно запущен")
            return self.driver
        except Exception as e:
            self.logger.error(f"Ошибка при запуске драйвера: {e}")
            raise

    def navigate_to_page(self, url: str) -> None:
        """Переход на страницу"""
        try:
            self.logger.info(f"Переход на страницу: {url}")
            self.driver.get(url)
            self.driver.implicitly_wait(10)

            # Обработка диалогового окна
            handle_dialog_overlay(self.driver)

            # Выбор периода "8 days"
            select_period_8_days(self.driver)

            self.logger.info("Страница успешно загружена")
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке страницы: {e}")
            raise

    def navigate_to_page_basic(self, url: str) -> None:
        """Базовый переход без специфичных действий (для сторонних сайтов)"""
        try:
            self.logger.info(f"Базовый переход на страницу: {url}")
            self.driver.get(url)
            self.driver.implicitly_wait(10)
            self.logger.info("Страница успешно загружена (basic)")
        except Exception as e:
            self.logger.error(f"Ошибка при базовой загрузке страницы: {e}")
            raise

    def click_element_safely(self, xpath: str, timeout: int = 10) -> bool:
        """Безопасный клик по элементу"""
        try:
            self.logger.debug(f"Ожидание кликабельности: {xpath}, timeout={timeout}s")
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))

            try:
                element.click()
            except:
                # Если обычный клик не работает, используем JavaScript
                self.driver.execute_script("arguments[0].click();", element)

            self.logger.debug("Клик выполнен, ожидаем обновление контента...")
            time.sleep(2)  # Даем время на загрузку данных
            return True
        except Exception as e:
            # Сохраняем часть HTML для диагностики
            try:
                html_snippet = (self.driver.page_source or "")[:2000]
            except Exception:
                html_snippet = "<no page source>"
            self.logger.error(
                f"Ошибка при клике по элементу {xpath}: {e}. Фрагмент страницы: {html_snippet}"
            )
            return False

    def get_page_source(self) -> str:
        """Получение исходного кода страницы"""
        return self.driver.page_source

    def close_driver(self) -> None:
        """Закрытие драйвера"""
        if self.driver:
            try:
                # Закрываем все окна, если ещё открыты
                try:
                    handles = list(getattr(self.driver, "window_handles", []) or [])
                    for handle in handles:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except Exception:
                            pass
                except Exception:
                    pass
                # Финальный quit на сессию
                self.driver.quit()
                self.logger.info("Драйвер закрыт")
            except Exception as e:
                self.logger.error(f"Ошибка при закрытии драйвера: {e}")
            finally:
                # Пытаемся остановить сервис, если доступен
                try:
                    if getattr(self.driver, "service", None):
                        self.driver.service.stop()
                except Exception:
                    pass
                self.driver = None

    def __enter__(self):
        """Контекстный менеджер - вход"""
        self.start_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.close_driver()

    def _cleanup_at_exit(self) -> None:
        """Хук завершения процесса для гарантированного закрытия драйвера"""
        try:
            self.close_driver()
        except Exception:
            pass
