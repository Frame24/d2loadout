"""
Скрапер для сбора данных о героях Dota 2
"""

import pandas as pd
import time
import logging
from typing import Dict, List
from bs4 import BeautifulSoup

from ..core.scraping_manager import ScrapingManager

logger = logging.getLogger(__name__)


class HeroScraper:
    """Скрапер для сбора данных о героях"""

    def __init__(self):
        self.positions = {
            "pos 1": "//div[contains(text(), 'Carry')]",
            "pos 2": "//div[contains(text(), 'Mid')]",
            "pos 3": "//div[contains(text(), 'Off')]",
            "pos 4": "//div[contains(text(), 'Pos 4')]",
            "pos 5": "//div[contains(text(), 'Pos 5')]",
        }

    def scrape_heroes_data(
        self, url: str = "https://dota2protracker.com/meta"
    ) -> pd.DataFrame:
        """
        Сбор данных о героях

        Args:
            url: URL страницы с данными

        Returns:
            DataFrame с данными о героях
        """
        logger.info("Начало сбора данных о героях...")

        with ScrapingManager() as manager:
            manager.navigate_to_page(url)

            dfs = []

            # Проход по всем позициям и сбор данных
            for position, xpath in self.positions.items():
                logger.info(f"Сбор данных для {position}")

                # Кликаем по позиции
                if manager.click_element_safely(xpath):
                    # Получаем данные таблицы
                    df = self._extract_table_data(manager.driver)
                    df["Role"] = position
                    dfs.append(df)
                else:
                    logger.error(f"Не удалось кликнуть по позиции {position}")

            if dfs:
                df_full = pd.concat(dfs, axis=0)
                logger.info("Сбор данных о героях завершен")
                return df_full
            else:
                logger.error("Не удалось собрать данные о героях")
                return pd.DataFrame()

    def _extract_table_data(self, driver) -> pd.DataFrame:
        """
        Извлечение данных из таблицы

        Args:
            driver: WebDriver instance

        Returns:
            DataFrame с данными таблицы
        """
        time.sleep(0.2)

        # Получаем HTML страницы
        page_source = driver.page_source

        # Парсим HTML с помощью BeautifulSoup
        soup = BeautifulSoup(page_source, "html.parser")

        # Ищем строки таблицы по их CSS-классу
        table_rows = soup.find_all("div", class_="grid", style=True)

        # Список для хранения данных
        data = []
        headers = []

        for index, row in enumerate(table_rows):
            # Проверяем, чтобы строка не была заголовком
            cols = row.find_all("div", recursive=False)

            if index == 0:
                # Считаем первую строку заголовком
                for col in cols:
                    header_text = col.get_text(strip=True)
                    headers.append(header_text if header_text else None)
                continue

            row_data = []
            for col in cols:
                # Проверяем наличие изображений для извлечения роли
                img = col.find("img", alt=True)
                if img:
                    row_data.append(img["alt"])
                    continue

                # Обрабатываем содержимое внутри span
                spans = col.find_all("span")
                if spans:
                    span_text = " ".join([span.get_text(strip=True) for span in spans])
                    row_data.append(span_text if span_text else None)
                    continue

                # Извлекаем текст и убираем пустые значения
                text = col.get_text(strip=True)
                row_data.append(text if text else None)

            if row_data:  # Только если данные не пусты
                data.append(row_data)

        # Преобразуем список в DataFrame
        df_heroes_table = pd.DataFrame(data, columns=headers)

        # Убираем лишние строки или обрабатываем некорректные данные
        df_heroes_table = df_heroes_table.dropna(how="all")

        # Очистка данных в процентах и диапазонах
        df_heroes_table = self._clean_data(df_heroes_table)

        return df_heroes_table

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Очистка данных в DataFrame

        Args:
            df: DataFrame для очистки

        Returns:
            Очищенный DataFrame
        """

        def clean_data(value):
            if isinstance(value, str):
                if "%" in value:
                    try:
                        return float(value.replace("%", ""))
                    except ValueError:
                        return value
                elif "(" in value and ")" in value:
                    try:
                        main_value, range_values = value.split("(")
                        main_value = main_value.strip()
                        range_values = range_values.replace(")", "").split("-")
                        return {
                            "main": int(main_value),
                            "range_min": int(range_values[0]),
                            "range_max": int(range_values[1]),
                        }
                    except ValueError:
                        return value
            return value

        # Применяем очистку данных ко всем ячейкам
        df = df.map(clean_data)

        # Обработка типов данных для чисел
        df = df.apply(lambda x: x.convert_dtypes() if x.name != 2 else x)

        return df
