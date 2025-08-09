"""
Основной скрипт для запуска Dota 2 Data Scraper
"""

import argparse
import sys
import logging
from typing import Optional

from modules.scrapers.hero_scraper import HeroScraper
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
    """Запуск скрапинга героев (теперь включает все данные)"""
    try:
        logger.info("Запуск полного скрапинга данных...")
        scraper = HeroScraper(headless=getattr(run_heroes_scraping, "_headless", True))
        data_manager = DataManager()

        # Сбор данных
        heroes_df = scraper.scrape_heroes_data()

        if not heroes_df.empty:
            # Сохранение данных
            success = data_manager.save_dataframe(heroes_df, "heroes_data.csv")
            if success:
                logger.info("✅ Скрапинг данных завершен успешно")
                return True
            else:
                logger.error("❌ Ошибка при сохранении данных")
                return False
        else:
            logger.error("❌ Не удалось собрать данные")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при скрапинге: {e}")
        return False


def run_heroes_no_facets_scraping() -> bool:
    """Запуск скрапинга героев без фасетов (группировка фасетов)"""
    try:
        logger.info("Запуск скрапинга данных без фасетов...")
        scraper = HeroScraper(headless=getattr(run_heroes_scraping, "_headless", True))
        data_manager = DataManager()

        # Сбор данных без фасетов
        heroes_no_facets_df = scraper.scrape_heroes_no_facets()

        if not heroes_no_facets_df.empty:
            # Сохранение данных без фасетов
            success = data_manager.save_dataframe(
                heroes_no_facets_df, "heroes_no_facets.csv"
            )
            if success:
                logger.info("✅ Скрапинг данных без фасетов завершен успешно")
                return True
            else:
                logger.error("❌ Ошибка при сохранении данных без фасетов")
                return False
        else:
            logger.error("❌ Не удалось собрать данные без фасетов")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при скрапинге без фасетов: {e}")
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
    parser.add_argument(
        "--scrape", action="store_true", help="Запуск скрапинга всех данных"
    )
    parser.add_argument(
        "--scrape-no-facets",
        action="store_true",
        help="Запуск скрапинга данных без фасетов (группировка)",
    )
    parser.add_argument(
        "--config", action="store_true", help="Запуск обработки конфигураций"
    )
    parser.add_argument("--all", action="store_true", help="Запуск всех процессов")
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Запускать браузер Chrome в видимом режиме (без headless)",
    )

    args = parser.parse_args()

    # Протаскиваем настройку headless для скрапинга
    setattr(run_heroes_scraping, "_headless", not args.no_headless)

    success_count = 0
    total_count = 0

    # Определяем, какие процессы запускать
    if args.scrape:
        total_count += 1
        if run_heroes_scraping():
            success_count += 1
    elif args.scrape_no_facets:
        total_count += 1
        if run_heroes_no_facets_scraping():
            success_count += 1
    elif args.config:
        total_count += 1
        if run_config_processing():
            success_count += 1
    elif args.all or not any([args.scrape, args.scrape_no_facets, args.config]):
        # Запуск всех процессов
        logger.info("Запуск всех процессов...")

        total_count += 1
        if run_heroes_scraping():
            success_count += 1

        total_count += 1
        if run_heroes_no_facets_scraping():
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
