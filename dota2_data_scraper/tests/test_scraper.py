"""
Тесты для проверки корректности парсинга данных за последние 8 дней
"""

import unittest
import pandas as pd
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.scrapers.hero_scraper import HeroScraper
from modules.core.data_manager import DataManager
from modules.core.config_processor import ConfigProcessor


class TestDataScraper(unittest.TestCase):
    """Тесты для системы скрапинга данных"""

    def setUp(self):
        """Настройка тестов"""
        self.data_manager = DataManager()

    def test_heroes_data_exists_and_valid(self):
        """Тест проверки существования и валидности данных героев"""
        # Проверяем существование файла
        self.assertTrue(
            os.path.exists("heroes_data.csv"), "Файл heroes_data.csv не существует"
        )

        # Загружаем данные
        df = self.data_manager.load_dataframe("heroes_data.csv")
        self.assertIsNotNone(df, "Не удалось загрузить данные героев")
        self.assertFalse(df.empty, "Данные героев пусты")

        # Проверяем необходимые колонки
        required_columns = [
            "Hero",
            "Facet",
            "D2PT Rating",
            "Matches",
            "WR",
            "Role",
        ]
        for col in required_columns:
            self.assertIn(col, df.columns, f"Отсутствует колонка {col}")

        # Проверяем, что данные за последние 8 дней содержат все 5 позиций
        positions = df["Role"].unique()
        expected_positions = ["pos 1", "pos 2", "pos 3", "pos 4", "pos 5"]
        for pos in expected_positions:
            self.assertIn(pos, positions, f"Отсутствует позиция {pos}")

        # Проверяем, что для каждой позиции есть достаточно данных
        for pos in expected_positions:
            pos_data = df[df["Role"] == pos]
            self.assertGreater(len(pos_data), 0, f"Нет данных для позиции {pos}")
        # Проверяем, что есть непустые названия фасетов
        self.assertIn("Facet", df.columns)
        non_empty_facets = df["Facet"].dropna()
        self.assertGreater(len(non_empty_facets), 0, "Нет названий фасетов")

        print(
            f"✅ Данные героев корректны: {len(df)} записей, {len(positions)} позиций"
        )
        print(f"✅ Пример фасета: {non_empty_facets.iloc[0]}")

    def test_facet_numbers_correct(self):
        """Тест проверки корректности номеров фасетов (в processed_heroes.csv)"""
        if not os.path.exists("processed_heroes.csv"):
            self.skipTest("Файл processed_heroes.csv не существует")

        df = self.data_manager.load_dataframe("processed_heroes.csv")
        self.assertIsNotNone(df, "Не удалось загрузить обработанные данные")

        # Проверяем, что facet_number есть
        self.assertIn("facet_number", df.columns, "Отсутствует поле facet_number")

        # Проверяем примеры героев с фасетами
        test_heroes = ["Juggernaut", "Pudge", "Abaddon"]

        for hero in test_heroes:
            hero_data = df[df["Hero"] == hero]
            if not hero_data.empty:
                facet_numbers = sorted(hero_data["facet_number"].unique())
                self.assertGreaterEqual(
                    facet_numbers[0], 1, f"Первый фасет {hero} должен иметь номер >= 1"
                )

                # Проверяем последовательность без пропусков
                expected = list(
                    range(int(min(facet_numbers)), int(max(facet_numbers)) + 1)
                )
                self.assertEqual(
                    facet_numbers,
                    expected,
                    f"Номера фасетов {hero} должны быть последовательными: {expected}",
                )

        print("✅ Номера фасетов корректны для тестовых героев (processed)")

    def test_processed_data_has_hero_ids(self):
        """Тест проверки наличия hero_id в обработанных данных"""
        if not os.path.exists("processed_heroes.csv"):
            self.skipTest("Файл processed_heroes.csv не существует")

        df = self.data_manager.load_dataframe("processed_heroes.csv")
        self.assertIsNotNone(df, "Не удалось загрузить обработанные данные")

        # Проверяем наличие hero_id
        self.assertIn("hero_id", df.columns, "Отсутствует колонка hero_id")

        # Проверяем, что hero_id не пустые
        non_null_ids = df["hero_id"].notna().sum()
        self.assertGreater(non_null_ids, 0, "Все hero_id пустые")

        # Проверяем корректность некоторых известных ID
        nature_prophet = df[df["Hero"] == "Nature's Prophet"]["hero_id"].iloc[0]
        self.assertEqual(nature_prophet, 53.0, "Неверный ID для Nature's Prophet")

        print(f"✅ Hero ID корректны: {non_null_ids} из {len(df)} записей")

    def test_config_generation(self):
        """Тест проверки генерации конфигураций"""
        if not os.path.exists(os.path.join("configs", "hero_configs.json")):
            self.skipTest("Файл hero_configs.json не существует")

        import json

        with open(os.path.join("configs", "hero_configs.json"), "r") as f:
            config = json.load(f)

        # Проверяем структуру конфигурации
        self.assertIn("version", config, "Отсутствует версия конфигурации")
        self.assertIn("configs", config, "Отсутствуют конфигурации")

        # Проверяем, что есть ровно 2 конфигурации
        configs = config["configs"]
        self.assertEqual(len(configs), 2, "Должно быть ровно 2 конфигурации")

        # Проверяем названия конфигураций
        config_names = [cfg["config_name"] for cfg in configs]
        self.assertIn("Win rate", config_names, "Отсутствует конфигурация 'Win rate'")
        self.assertIn("D2PT", config_names, "Отсутствует конфигурация 'D2PT'")

        # Проверяем структуру первой конфигурации
        first_config = configs[0]
        required_fields = ["config_name", "categories"]
        for field in required_fields:
            self.assertIn(field, first_config, f"Отсутствует поле {field}")

        # Проверяем категории
        categories = first_config["categories"]
        self.assertGreater(len(categories), 0, "Нет категорий")

        # Проверяем структуру первой категории
        first_category = categories[0]
        required_category_fields = [
            "category_name",
            "x_position",
            "y_position",
            "width",
            "height",
            "hero_ids",
        ]
        for field in required_category_fields:
            self.assertIn(field, first_category, f"Отсутствует поле категории {field}")

        # Проверяем, что есть hero_ids
        hero_ids = first_category["hero_ids"]
        self.assertGreater(len(hero_ids), 0, "Нет hero_ids в категории")

        print(f"✅ Конфигурации корректны: {len(configs)} конфигураций")
        for i, cfg in enumerate(configs, 1):
            categories_count = len(cfg["categories"])
            heroes_count = sum(len(cat["hero_ids"]) for cat in cfg["categories"])
            print(
                f"  {i}. {cfg['config_name']}: {categories_count} категорий, {heroes_count} героев"
            )

    def test_data_freshness(self):
        """Тест проверки актуальности данных (последние 8 дней)"""
        if not os.path.exists("heroes_data.csv"):
            self.skipTest("Файл heroes_data.csv не существует")

        # Проверяем время модификации файла
        import time

        file_time = os.path.getmtime("heroes_data.csv")
        current_time = time.time()
        time_diff = current_time - file_time

        # Данные должны быть не старше 24 часов для актуальности
        max_age_hours = 24
        max_age_seconds = max_age_hours * 3600

        self.assertLess(
            time_diff,
            max_age_seconds,
            f"Данные устарели: {time_diff/3600:.1f} часов назад",
        )

        print(f"✅ Данные актуальны: {time_diff/3600:.1f} часов назад")


def run_tests():
    """Запуск всех тестов"""
    print("🧪 Запуск тестов системы парсинга данных...")

    # Создаем test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDataScraper)

    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Выводим результат
    if result.wasSuccessful():
        print("✅ Все тесты пройдены успешно!")
        return True
    else:
        print("❌ Некоторые тесты провалились")
        return False


if __name__ == "__main__":
    run_tests()
