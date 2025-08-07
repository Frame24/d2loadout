"""
Менеджер для работы с данными
"""

import pandas as pd
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)


class DataManager:
    """Менеджер для работы с данными"""

    def __init__(self, output_dir: str = "."):
        """
        Инициализация менеджера данных

        Args:
            output_dir: Директория для сохранения файлов
        """
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)

    def save_dataframe(self, df: pd.DataFrame, filename: str) -> bool:
        """
        Сохранение DataFrame в CSV файл

        Args:
            df: DataFrame для сохранения
            filename: Имя файла

        Returns:
            True если сохранение успешно, False в противном случае
        """
        try:
            filepath = os.path.join(self.output_dir, filename)
            df.to_csv(filepath, index=False)
            self.logger.info(f"Данные сохранены в {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении {filename}: {e}")
            return False

    def load_dataframe(self, filename: str) -> Optional[pd.DataFrame]:
        """
        Загрузка DataFrame из CSV файла

        Args:
            filename: Имя файла

        Returns:
            DataFrame или None если файл не найден
        """
        try:
            filepath = os.path.join(self.output_dir, filename)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                self.logger.info(f"Данные загружены из {filepath}")
                return df
            else:
                self.logger.warning(f"Файл {filepath} не найден")
                return None
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке {filename}: {e}")
            return None

    def merge_heroes_and_facets(
        self, heroes_df: pd.DataFrame, facets_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Объединение данных героев и фасетов

        Args:
            heroes_df: DataFrame с данными героев
            facets_df: DataFrame с данными фасетов

        Returns:
            Объединенный DataFrame
        """
        try:
            self.logger.info("Объединение данных героев и фасетов...")

            # Подготовка данных для объединения
            facets_df["facet_upper"] = facets_df["Facet"].str.upper()

            # Объединение данных
            merged_df = pd.merge(
                facets_df,
                heroes_df[["Hero", "hero_id"]],
                left_on="Hero",
                right_on="Hero",
                how="left",
            )

            # Очистка и реорганизация колонок
            merged_df = merged_df.drop(columns=["facet_upper"])

            # Добавляем facet_number если его нет
            if "facet_number" not in merged_df.columns:
                merged_df["facet_number"] = merged_df.groupby(["Hero"]).cumcount() + 1

            merged_df = merged_df[
                [
                    "hero_id",
                    "Hero",
                    "Facet",
                    "Matches",
                    "Win Rate",
                    "Role",
                    "facet_number",
                ]
            ]

            self.logger.info("Объединение данных завершено")
            return merged_df

        except Exception as e:
            self.logger.error(f"Ошибка при объединении данных: {e}")
            return pd.DataFrame()

    def get_file_info(self, filename: str) -> dict:
        """
        Получение информации о файле

        Args:
            filename: Имя файла

        Returns:
            Словарь с информацией о файле
        """
        filepath = os.path.join(self.output_dir, filename)
        if os.path.exists(filepath):
            stat = os.stat(filepath)
            return {
                "exists": True,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "path": filepath,
            }
        else:
            return {"exists": False}

    def list_data_files(self) -> list:
        """
        Список всех CSV файлов в директории

        Returns:
            Список имен файлов
        """
        try:
            files = [f for f in os.listdir(self.output_dir) if f.endswith(".csv")]
            return sorted(files)
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка файлов: {e}")
            return []
