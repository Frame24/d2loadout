"""
Основной скрипт для запуска Dota 2 Data Scraper
"""

import argparse
import sys
import logging
from typing import Optional

from modules.scrapers.hero_scraper import HeroScraper
from modules.scrapers.facet_scraper import FacetScraper
from modules.core.data_manager import DataManager
from modules.core.config_processor import ConfigProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Проверка зависимостей"""
    try:
        import selenium

        logger.info(f"Selenium установлен, версия: {selenium.__version__}")
        return True
    except ImportError:
        logger.error(
            "❌ Selenium не найден. Установите его с помощью 'pip install selenium'."
        )
        return False


def run_heroes_scraping() -> bool:
    """Запуск скрапинга героев"""
    try:
        logger.info("Запуск скрапинга героев...")
        scraper = HeroScraper()
        data_manager = DataManager()

        # Сбор данных
        heroes_df = scraper.scrape_heroes_data()

        if not heroes_df.empty:
            # Сохранение данных
            success = data_manager.save_dataframe(heroes_df, "heroes_data.csv")
            if success:
                logger.info("✅ Скрапинг героев завершен успешно")
                return True
            else:
                logger.error("❌ Ошибка при сохранении данных героев")
                return False
        else:
            logger.error("❌ Не удалось собрать данные героев")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при скрапинге героев: {e}")
        return False


def run_facets_scraping() -> bool:
    """Запуск скрапинга фасетов"""
    try:
        logger.info("Запуск скрапинга фасетов...")
        scraper = FacetScraper()
        data_manager = DataManager()

        # Сбор данных
        facets_df = scraper.scrape_facets_data()

        if not facets_df.empty:
            # Сохранение данных
            success = data_manager.save_dataframe(facets_df, "facets_data.csv")
            if success:
                logger.info("✅ Скрапинг фасетов завершен успешно")
                return True
            else:
                logger.error("❌ Ошибка при сохранении данных фасетов")
                return False
        else:
            logger.error("❌ Не удалось собрать данные фасетов")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при скрапинге фасетов: {e}")
        return False


def run_config_processing() -> bool:
    """Запуск обработки конфигураций"""
    try:
        logger.info("Запуск обработки конфигураций...")
        processor = ConfigProcessor()

        # Обработка данных
        success = processor.process_all_data()
        if success:
            logger.info("✅ Обработка конфигураций завершена успешно")
            return True
        else:
            logger.error("❌ Ошибка при обработке конфигураций")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке конфигураций: {e}")
        return False


def main():
    """Основная функция"""
    # Проверка зависимостей
    if not check_dependencies():
        sys.exit(1)

    # Настройка аргументов командной строки
    parser = argparse.ArgumentParser(description="Dota 2 Data Scraper")
    parser.add_argument("--heroes", action="store_true", help="Запуск скрапинга героев")
    parser.add_argument(
        "--facets", action="store_true", help="Запуск скрапинга фасетов"
    )
    parser.add_argument(
        "--config", action="store_true", help="Запуск обработки конфигураций"
    )
    parser.add_argument("--all", action="store_true", help="Запуск всех процессов")

    args = parser.parse_args()

    success_count = 0
    total_count = 0

    # Определяем, какие процессы запускать
    if args.heroes:
        total_count += 1
        if run_heroes_scraping():
            success_count += 1
    elif args.facets:
        total_count += 1
        if run_facets_scraping():
            success_count += 1
    elif args.config:
        total_count += 1
        if run_config_processing():
            success_count += 1
    elif args.all or not any([args.heroes, args.facets, args.config]):
        # Запуск всех процессов
        logger.info("Запуск всех процессов...")

        total_count += 1
        if run_heroes_scraping():
            success_count += 1

        total_count += 1
        if run_facets_scraping():
            success_count += 1

        total_count += 1
        if run_config_processing():
            success_count += 1

    # Итоговый отчет
    logger.info(f"Все процессы завершены. Успешно: {success_count}/{total_count}")

    if success_count == total_count:
        logger.info("✅ Все процессы выполнены успешно!")
        return 0
    else:
        logger.error(
            f"❌ {total_count - success_count} процессов завершились с ошибками"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
