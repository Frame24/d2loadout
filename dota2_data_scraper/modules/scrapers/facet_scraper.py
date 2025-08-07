"""
Скрапер для сбора данных о фасетах героев Dota 2
"""

import pandas as pd
import time
import logging
import re
import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

from ..core.scraping_manager import ScrapingManager

logger = logging.getLogger(__name__)


class FacetScraper:
    """Скрапер для сбора данных о фасетах"""

    def __init__(self):
        self.positions = {
            "pos 1": "//div[contains(text(), 'Carry')]",
            "pos 2": "//div[contains(text(), 'Mid')]",
            "pos 3": "//div[contains(text(), 'Off')]",
            "pos 4": "//div[contains(text(), 'Pos 4')]",
            "pos 5": "//div[contains(text(), 'Pos 5')]",
        }

    def scrape_facets_data(
        self, url: str = "https://dota2protracker.com/facets"
    ) -> pd.DataFrame:
        """
        Сбор данных о фасетах

        Args:
            url: URL страницы с фасетами

        Returns:
            DataFrame с данными о фасетах
        """
        logger.info("Начало сбора данных о фасетах...")

        with ScrapingManager() as manager:
            manager.navigate_to_page(url)

            dfs = []

            # Проход по всем позициям и сбор данных
            for position, xpath in self.positions.items():
                logger.info(f"Сбор данных фасетов для {position}")

                # Кликаем по позиции
                if manager.click_element_safely(xpath):
                    # Получаем данные таблицы
                    df = self._extract_facets_table_data(manager.driver)
                    df["Role"] = position
                    dfs.append(df)
                else:
                    logger.error(f"Не удалось кликнуть по позиции {position}")

            if dfs:
                df_full = pd.concat(dfs, axis=0)
                # Очистка данных
                df_full["Win Rate"] = df_full["Win Rate"].apply(
                    lambda x: x.replace("%", "")
                )
                df_full = df_full.convert_dtypes()

                logger.info("Сбор данных о фасетах завершен")
                return df_full
            else:
                logger.error("Не удалось собрать данные о фасетах")
                return pd.DataFrame()

    def _extract_facets_table_data(self, driver) -> pd.DataFrame:
        """
        Извлечение данных таблицы фасетов

        Args:
            driver: WebDriver instance

        Returns:
            DataFrame с данными таблицы фасетов
        """
        logger.info("Извлечение данных таблицы фасетов...")
        time.sleep(0.2)

        # Извлекаем строки таблицы с сайта
        category_name_elements = driver.find_elements(
            "css selector", ".flex.bg-d2pt-gray-3.gap-1"
        )
        category_name_elements += driver.find_elements(
            "css selector", ".flex.bg-d2pt-gray-4.gap-1"
        )

        hero_rows = [item.text.split("\n") for item in category_name_elements]
        hero_columns = [
            item
            for item in driver.find_element(
                "css selector", ".flex.gap-1.font-medium.text-sm.mb-1"
            ).text.split("\n")
            if item != "Trend"
        ]

        # Преобразование данных в DataFrame
        df_heroes_table = pd.DataFrame(data=hero_rows, columns=hero_columns)
        df_heroes_table = df_heroes_table.convert_dtypes()
        df_heroes_table = df_heroes_table.round(1)

        logger.info("Извлечение таблицы фасетов завершено")
        return df_heroes_table

    def fetch_hero_facets(self, hero_url: str) -> Optional[Dict]:
        """
        Получение данных фасетов конкретного героя

        Args:
            hero_url: URL страницы героя

        Returns:
            Словарь с данными фасетов или None
        """
        try:
            logger.info(f"Получение фасетов для: {hero_url}")

            response = requests.get(hero_url)
            response.raise_for_status()

            html_text = response.text

            # Регулярное выражение для извлечения объекта facetData
            pattern = r"facetData:\s*({.*?})\s*\}\s*,"
            match = re.findall(pattern, html_text, re.DOTALL)

            if match:
                # Парсим JSON данные
                import json

                facet_data = json.loads(match[0])
                logger.info("Данные фасетов успешно получены")
                return facet_data
            else:
                logger.warning("Данные фасетов не найдены в HTML")
                return None

        except Exception as e:
            logger.error(f"Ошибка при получении фасетов: {e}")
            return None

    def process_facets_data(self, facet_data: Dict) -> pd.DataFrame:
        """
        Обработка полученных данных фасетов

        Args:
            facet_data: Словарь с данными фасетов

        Returns:
            DataFrame с обработанными данными
        """
        logger.info("Обработка данных фасетов...")
        all_facets_df = pd.DataFrame()

        # Итерация по всем ключам в facetData
        for key, value in facet_data.items():
            facets = value.get("facets", [])

            # Преобразуем каждый набор facets в DataFrame
            facets_data = []
            for facet in facets:
                if not facet.get("deprecated", False):  # Пропускаем устаревшие данные
                    facets_data.append(facet)

            facets_df = pd.DataFrame(facets_data)

            # Добавляем информацию о ключе, id и имени героя в DataFrame
            facets_df["key"] = key
            facets_df["id"] = value.get("id")
            facets_df["localized_name"] = value.get("localized_name")

            # Объединяем текущий DataFrame с общим
            all_facets_df = pd.concat([all_facets_df, facets_df], ignore_index=True)

        # Перенумерация facet_number
        all_facets_df["facet_number"] = (
            all_facets_df.groupby(["key", "id"]).cumcount() + 1
        )

        logger.info("Обработка фасетов завершена")
        return all_facets_df
