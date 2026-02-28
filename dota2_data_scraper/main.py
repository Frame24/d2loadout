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


def setup_logging(quiet_mode: bool = False, debug_mode: bool = False):
    """Настройка логирования в зависимости от режима"""
    if debug_mode:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
            force=True,
        )
        return
    if quiet_mode:
        # Тихий режим - только критические ошибки и пользовательские сообщения
        logging.basicConfig(
            level=logging.CRITICAL,
            format="%(message)s",
            handlers=[logging.StreamHandler()],
            force=True,
        )
        # Отключаем логи всех модулей
        logging.getLogger("selenium").setLevel(logging.CRITICAL)
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)
        logging.getLogger("WDM").setLevel(logging.CRITICAL)
        logging.getLogger("webdriver_manager").setLevel(logging.CRITICAL)
        logging.getLogger("modules").setLevel(logging.CRITICAL)
        logging.getLogger("modules.scrapers").setLevel(logging.CRITICAL)
        logging.getLogger("modules.core").setLevel(logging.CRITICAL)
        logging.getLogger("modules.utils").setLevel(logging.CRITICAL)
        logging.getLogger("modules.scrapers.hero_scraper").setLevel(logging.CRITICAL)
        logging.getLogger("modules.core.scraping_manager").setLevel(logging.CRITICAL)
        logging.getLogger("modules.core.data_manager").setLevel(logging.CRITICAL)
        logging.getLogger("modules.utils.facet_api_parser").setLevel(logging.CRITICAL)
        logging.getLogger("modules.utils.dialog_handler").setLevel(logging.CRITICAL)
        logging.getLogger("modules.utils.period_selector").setLevel(logging.CRITICAL)
        # Отключаем корневой логгер для всех модулей
        logging.getLogger().setLevel(logging.CRITICAL)
    else:
        # Обычный режим
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,
        )


# Временная настройка логирования (будет переопределена в main)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для режима
QUIET_MODE = False
DEBUG_MODE = False


def user_print(message: str):
    """Печать сообщений для пользователя в любом режиме"""
    if QUIET_MODE:
        print(message)
    else:
        logger.info(message)


def _print_preview_first_rows(
    df, role: str = "pos 4", rows: int = 10
):
    """Печатает первые N строк по позиции: №, Hero, Facet, facet_number."""
    if df.empty or "Hero" not in df.columns or "Facet" not in df.columns:
        return
    if "Role" not in df.columns:
        subset = df.head(rows)
    else:
        subset = df[df["Role"] == role].head(rows)
    if subset.empty:
        return
    has_num = "facet_number" in df.columns
    user_print(f"Первые {len(subset)} строк (позиция: {role}):")
    user_print(f"{'№':<4} {'Hero':<25} {'Facet':<30} {'facet_number' if has_num else ''}")
    user_print("-" * (4 + 25 + 30 + (15 if has_num else 0)))
    for i, (_, row) in enumerate(subset.iterrows(), 1):
        hero = str(row.get("Hero", ""))[:24]
        facet = str(row.get("Facet", ""))[:29]
        num = row.get("facet_number", "") if has_num else ""
        user_print(f"{i:<4} {hero:<25} {facet:<30} {num}")


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


def run_full_scraping() -> tuple[bool, bool]:
    """
    Запуск полного скрапинга данных - собирает оба типа данных за один проход

    Returns:
        tuple: (успех_с_фасетами, успех_без_фасетов)
    """
    try:
        user_print("Запуск сбора данных с dota2protracker.com...")
        scraper = HeroScraper(
            headless=getattr(run_full_scraping, "_headless", True),
            debug_dotabuff=getattr(run_full_scraping, "_debug_dotabuff", False),
        )
        data_manager = DataManager()

        # Эффективный сбор обоих типов данных за один проход
        user_print("Собираем статистику героев...")
        heroes_df, heroes_no_facets_df = scraper.scrape_both_data_types(
            show_progress=QUIET_MODE
        )

        if not heroes_df.empty:
            _print_preview_first_rows(heroes_df, role="pos 4", rows=10)

        # Сохранение данных с фасетами (в CSV номер фасета не сохраняем)
        success_with_facets = False
        if not heroes_df.empty:
            to_save = heroes_df.drop(columns=["facet_number"], errors="ignore")
            success_with_facets = data_manager.save_dataframe(
                to_save, "heroes_data.csv"
            )
            if success_with_facets:
                user_print("OK - Данные с фасетами сохранены")
            else:
                user_print("ERROR - Ошибка при сохранении данных с фасетами")
        else:
            user_print("ERROR - Не удалось собрать данные с фасетами")

        # Сохранение данных без фасетов
        success_no_facets = False
        if not heroes_no_facets_df.empty:
            success_no_facets = data_manager.save_dataframe(
                heroes_no_facets_df, "heroes_no_facets.csv"
            )
            if success_no_facets:
                user_print("OK - Данные без фасетов сохранены")
            else:
                user_print("ERROR - Ошибка при сохранении данных без фасетов")
        else:
            user_print("ERROR - Не удалось собрать данные без фасетов")

        return success_with_facets, success_no_facets

    except Exception as e:
        user_print(f"ERROR - Ошибка при сборе данных: {e}")
        return False, False


def run_heroes_scraping() -> bool:
    """Запуск скрапинга героев с фасетами"""
    try:
        user_print("Запуск сбора данных с фасетами...")
        scraper = HeroScraper(
            headless=getattr(run_heroes_scraping, "_headless", True),
            debug_dotabuff=getattr(run_heroes_scraping, "_debug_dotabuff", False),
        )
        data_manager = DataManager()

        # Сбор данных
        heroes_df = scraper.scrape_heroes_data(show_progress=QUIET_MODE)

        if not heroes_df.empty:
            _print_preview_first_rows(heroes_df, role="pos 4", rows=10)
            to_save = heroes_df.drop(columns=["facet_number"], errors="ignore")
            success = data_manager.save_dataframe(to_save, "heroes_data.csv")
            if success:
                logger.info("✅ Скрапинг данных с фасетами завершен успешно")
                return True
            else:
                logger.error("❌ Ошибка при сохранении данных с фасетами")
                return False
        else:
            logger.error("❌ Не удалось собрать данные с фасетами")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при скрапинге с фасетами: {e}")
        return False


def run_heroes_no_facets_scraping() -> bool:
    """Запуск скрапинга героев без фасетов"""
    try:
        logger.info("Запуск скрапинга данных без фасетов...")
        scraper = HeroScraper(
            headless=getattr(run_heroes_scraping, "_headless", True),
            debug_dotabuff=getattr(run_heroes_scraping, "_debug_dotabuff", False),
        )
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
        user_print("Обрабатываем данные и создаем конфигурации...")
        processor = ConfigProcessor()

        # Обработка данных
        success = processor.process_all_data()
        if success:
            user_print("OK - Конфигурации созданы и скопированы в Steam")
            return True
        else:
            user_print("ERROR - Ошибка при обработке конфигураций")
            return False

    except Exception as e:
        user_print(f"ERROR - Ошибка при обработке конфигураций: {e}")
        return False


def main():
    """Основная функция"""
    global QUIET_MODE

    # Предварительная настройка для парсинга аргументов
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--quiet", action="store_true")
    args, _ = parser.parse_known_args()

    # Настройка логирования
    QUIET_MODE = args.quiet
    global DEBUG_MODE
    DEBUG_MODE = getattr(args, "debug", False)
    # Если включен дебаг — тихий режим игнорируем
    if DEBUG_MODE:
        QUIET_MODE = False
    setup_logging(QUIET_MODE, DEBUG_MODE)

    # Проверка зависимостей
    if not check_dependencies():
        sys.exit(1)

    # Настройка аргументов командной строки
    parser = argparse.ArgumentParser(
        description="Dota 2 Data Scraper - автоматизированный сбор данных о героях с dota2protracker.com",
        epilog="""
Примеры использования:
  run_d2loadout.bat                 # Автоматическая установка и запуск
  python main.py --quiet            # Тихий режим - минимум логов
  python main.py                    # Полный процесс с подробными логами
  python main.py --scrape-all       # Только оптимизированный скрапинг
  python main.py --config           # Только обработка конфигураций
  python main.py --no-headless      # Видимый режим браузера для отладки
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Скрапинг только данных с фасетами (отдельная сессия браузера)",
    )
    parser.add_argument(
        "--scrape-no-facets",
        action="store_true",
        help="Скрапинг только данных без фасетов (отдельная сессия браузера)",
    )
    parser.add_argument(
        "--scrape-all",
        action="store_true",
        help="ОПТИМИЗИРОВАННЫЙ скрапинг - оба типа данных за один проход браузера",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Обработка CSV данных и создание конфигураций для Dota 2",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Полный процесс: оптимизированный скрапинг + обработка конфигураций",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Показывать браузер Chrome (полезно для отладки)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Тихий режим - минимум логов для пользователей",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Расширенное логирование и диагностика",
    )
    parser.add_argument(
        "--debug-dotabuff",
        action="store_true",
        help="DEBUG: Попытка получения фасетов через Dotabuff с Selenium",
    )

    args = parser.parse_args()

    # Протаскиваем настройки для скрапинга
    setattr(run_heroes_scraping, "_headless", not args.no_headless)
    setattr(run_full_scraping, "_headless", not args.no_headless)
    setattr(run_heroes_scraping, "_debug_dotabuff", args.debug_dotabuff)
    setattr(run_full_scraping, "_debug_dotabuff", args.debug_dotabuff)

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
    elif args.scrape_all:
        # Оптимизированный скрапинг - оба типа данных за один проход
        if not QUIET_MODE:
            logger.info("Запуск оптимизированного скрапинга...")
        total_count += 2  # Считаем как 2 процесса
        success_with_facets, success_no_facets = run_full_scraping()
        if success_with_facets:
            success_count += 1
        if success_no_facets:
            success_count += 1
    elif args.config:
        total_count += 1
        if run_config_processing():
            success_count += 1
    elif args.all or not any(
        [args.scrape, args.scrape_no_facets, args.scrape_all, args.config]
    ):
        # Запуск всех процессов с оптимизацией
        if not QUIET_MODE:
            logger.info("Запуск всех процессов (оптимизированный)...")

        # Оптимизированный скрапинг
        total_count += 2  # Скрапинг считаем как 2 процесса
        success_with_facets, success_no_facets = run_full_scraping()
        if success_with_facets:
            success_count += 1
        if success_no_facets:
            success_count += 1

        # Обработка конфигураций
        total_count += 1
        if run_config_processing():
            success_count += 1

    # Итоговый отчет
    if QUIET_MODE:
        if success_count == total_count:
            user_print("ГОТОВО! Конфигурации обновлены в Dota 2")
        else:
            user_print(
                f"WARNING - Завершено с ошибками: {total_count - success_count} из {total_count}"
            )
    else:
        logger.info(f"Все процессы завершены. Успешно: {success_count}/{total_count}")

    if success_count == total_count:
        if not QUIET_MODE:
            logger.info("✅ Все процессы выполнены успешно!")
        return 0
    else:
        if not QUIET_MODE:
            logger.error(
                f"❌ {total_count - success_count} процессов завершились с ошибками"
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
