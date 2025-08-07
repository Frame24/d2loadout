"""
Процессор для создания конфигураций героев
"""

import pandas as pd
import json
import logging
from typing import Dict, List, Optional

from .data_manager import DataManager
from ..config.hero_config import HeroConfigProcessor

logger = logging.getLogger(__name__)


class ConfigProcessor:
    """Процессор для создания конфигураций"""

    def __init__(self):
        self.data_manager = DataManager()
        self.logger = logging.getLogger(__name__)

    def process_all_data(self) -> bool:
        """
        Обработка всех данных и создание конфигураций

        Returns:
            True если обработка успешна, False в противном случае
        """
        try:
            self.logger.info("Начало обработки всех данных...")

            # Загрузка данных
            heroes_df = self.data_manager.load_dataframe("heroes_data.csv")
            facets_df = self.data_manager.load_dataframe("facets_data.csv")

            if heroes_df is None or facets_df is None:
                self.logger.error("Не удалось загрузить необходимые данные")
                return False

            # Обработка данных героев
            processed_heroes = self._process_heroes_data(heroes_df)
            if processed_heroes.empty:
                self.logger.error("Ошибка при обработке данных героев")
                return False

            # Обработка данных фасетов
            processed_facets = self._process_facets_data(facets_df, heroes_df)
            if processed_facets.empty:
                self.logger.error("Ошибка при обработке данных фасетов")
                return False

            # Сохранение обработанных данных
            self.data_manager.save_dataframe(processed_heroes, "processed_heroes.csv")
            self.data_manager.save_dataframe(processed_facets, "processed_facets.csv")

            # Создание конфигураций
            config = self._create_configs(processed_heroes, processed_facets)

            # Сохранение конфигурации
            self._save_config(config)

            self.logger.info("Обработка всех данных завершена успешно")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при обработке данных: {e}")
            return False

    def _process_heroes_data(self, heroes_df: pd.DataFrame) -> pd.DataFrame:
        """
        Обработка данных героев

        Args:
            heroes_df: DataFrame с данными героев

        Returns:
            Обработанный DataFrame
        """
        try:
            self.logger.info("Обработка данных героев...")

            # Добавление hero_id (пока заглушка)
            heroes_df["hero_id"] = range(1, len(heroes_df) + 1)

            # Исправляем идентификатор героя "Outworld Destroyer"
            heroes_df.loc[heroes_df["Hero"] == "Outworld Destroyer", "hero_id"] = 76

            # Выбираем нужные колонки
            cols = [
                "hero_id",
                "Hero",
                "D2PT Rating",
                "Matches",
                "WR",
                "Most Played Build WR",
                "Role",
            ]
            processed_df = heroes_df[cols]

            self.logger.info("Обработка данных героев завершена")
            return processed_df

        except Exception as e:
            self.logger.error(f"Ошибка при обработке данных героев: {e}")
            return pd.DataFrame()

    def _process_facets_data(
        self, facets_df: pd.DataFrame, heroes_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Обработка данных фасетов

        Args:
            facets_df: DataFrame с данными фасетов
            heroes_df: DataFrame с данными героев

        Returns:
            Обработанный DataFrame
        """
        try:
            self.logger.info("Обработка данных фасетов...")

            # Объединение данных
            merged_df = self.data_manager.merge_heroes_and_facets(heroes_df, facets_df)

            if merged_df.empty:
                self.logger.error("Не удалось объединить данные фасетов")
                return pd.DataFrame()

            self.logger.info("Обработка данных фасетов завершена")
            return merged_df

        except Exception as e:
            self.logger.error(f"Ошибка при обработке данных фасетов: {e}")
            return pd.DataFrame()

    def _create_configs(self, heroes_df: pd.DataFrame, facets_df: pd.DataFrame) -> Dict:
        """
        Создание конфигураций

        Args:
            heroes_df: DataFrame с данными героев
            facets_df: DataFrame с данными фасетов

        Returns:
            Словарь с конфигурациями
        """
        try:
            self.logger.info("Создание конфигураций...")

            config = {
                "version": 3,
                "configs": [
                    # Фасеты
                    HeroConfigProcessor(
                        facets_df, "Facet Matches>200", data_type="facet"
                    ).build_config(matches_threshold=200, wr_threshold=51),
                    HeroConfigProcessor(
                        facets_df, "Facet Matches>50", data_type="facet"
                    ).build_config(matches_threshold=50, wr_threshold=51),
                    # Регулярные конфигурации
                    HeroConfigProcessor(
                        heroes_df, "WR", data_type="regular"
                    ).build_config(matches_threshold=200, wr_threshold=51),
                    HeroConfigProcessor(
                        heroes_df, "D2PT", data_type="regular"
                    ).build_config(
                        matches_threshold=200, wr_threshold=0, sort_by="D2PT Rating"
                    ),
                ],
            }

            self.logger.info("Конфигурации созданы успешно")
            return config

        except Exception as e:
            self.logger.error(f"Ошибка при создании конфигураций: {e}")
            return {}

    def _save_config(self, config: Dict) -> bool:
        """
        Сохранение конфигурации в файл

        Args:
            config: Словарь с конфигурацией

        Returns:
            True если сохранение успешно, False в противном случае
        """
        try:
            with open("hero_configs.json", "w") as config_file:
                json.dump(config, config_file, indent=4, default=str)

            self.logger.info("Конфигурация сохранена в hero_configs.json")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при сохранении конфигурации: {e}")
            return False
