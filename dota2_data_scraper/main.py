"""
Основной скрипт для запуска Dota 2 Data Scraper (API + конфиги).
"""

import argparse
import sys
import logging

from modules.scrapers.hero_stats_api import fetch_heroes_stats_safe
from modules.core.data_manager import DataManager
from modules.core.config_processor import ConfigProcessor


def _try_reconfigure_stdio_utf8() -> None:
    """Чтобы русский текст в логах не превращался в кракозябры в консоли Windows."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError, AttributeError):
                pass


def setup_logging(quiet_mode: bool = False, debug_mode: bool = False):
    """Настройка логирования в зависимости от режима"""
    _try_reconfigure_stdio_utf8()
    if debug_mode:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
            force=True,
        )
        return
    if quiet_mode:
        logging.basicConfig(
            level=logging.CRITICAL,
            format="%(message)s",
            handlers=[logging.StreamHandler()],
            force=True,
        )
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)
        logging.getLogger("modules").setLevel(logging.CRITICAL)
        logging.getLogger("modules.scrapers").setLevel(logging.CRITICAL)
        logging.getLogger("modules.core").setLevel(logging.CRITICAL)
        logging.getLogger("modules.utils").setLevel(logging.CRITICAL)
        logging.getLogger("modules.core.data_manager").setLevel(logging.CRITICAL)
        logging.getLogger().setLevel(logging.CRITICAL)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,
        )


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUIET_MODE = False
DEBUG_MODE = False


def user_print(message: str):
    """Печать сообщений для пользователя в любом режиме"""
    if QUIET_MODE:
        print(message)
    else:
        logger.info(message)


def _print_preview_first_rows(df, role: str = "pos 4", rows: int = 10):
    """Печатает первые N строк по позиции (Hero, Role, Matches, WR, D2PT)."""
    if df.empty or "Hero" not in df.columns:
        return
    if "Role" not in df.columns:
        subset = df.head(rows)
    else:
        subset = df[df["Role"] == role].head(rows)
    if subset.empty:
        return
    user_print(f"Первые {len(subset)} строк (позиция: {role}):")
    cols = ["Hero"]
    if "Matches" in subset.columns:
        cols.append("Matches")
    if "WR" in subset.columns:
        cols.append("WR")
    if "D2PT Rating" in subset.columns:
        cols.append("D2PT Rating")
    header = f"{'№':<4} " + " ".join(f"{c:<14}" for c in cols)
    user_print(header)
    user_print("-" * len(header))
    for i, (_, row) in enumerate(subset.iterrows(), 1):
        parts = [f"{i:<4}"]
        for c in cols:
            v = row.get(c, "")
            parts.append(f"{str(v)[:13]:<14}")
        user_print(" ".join(parts))


def check_core_dependencies() -> bool:
    """Минимальные зависимости для API-пайплайна."""
    try:
        import pandas  # noqa: F401
        import requests  # noqa: F401
    except ImportError as e:
        logger.error(
            f"❌ Не установлена зависимость ({e.name}). "
            "Выполните: pip install -r requirements.txt"
        )
        return False
    return True


def run_api_scraping(*, period: str, min_matches: int, mmr: int) -> bool:
    """Сбор heroes_data.csv через API dota2protracker (без браузера)."""
    try:
        user_print(
            f"Сбор статистики через D2PT API (heroes/stats)... "
            f"(period={period}, min_matches={min_matches}, mmr={mmr})"
        )
        data_manager = DataManager()
        heroes_df, err = fetch_heroes_stats_safe(
            period=period, min_matches=min_matches, mmr=mmr
        )
        if err:
            user_print(f"ERROR - {err}")
            return False
        if heroes_df.empty:
            user_print("ERROR - API не вернул данных")
            return False
        _print_preview_first_rows(heroes_df, role="pos 4", rows=10)
        if data_manager.save_dataframe(heroes_df, "heroes_data.csv"):
            user_print("OK - heroes_data.csv сохранён (API)")
            return True
        user_print("ERROR - не удалось сохранить heroes_data.csv")
        return False
    except Exception as e:
        user_print(f"ERROR - сбор через API: {e}")
        return False


def run_config_processing() -> bool:
    """Запуск обработки конфигураций"""
    try:
        user_print("Обрабатываем данные и создаем конфигурации...")
        processor = ConfigProcessor()

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
    global QUIET_MODE, DEBUG_MODE

    parser = argparse.ArgumentParser(
        description="Dota 2 Loadout - D2PT API и конфигурации героев",
        epilog="""
Примеры использования:
  run_d2loadout.bat                 # API + конфиги
  python main.py --quiet            # Тихий режим
  python main.py                    # API + конфиги с логами
  python main.py --config           # Только обработка CSV → hero_configs.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Обработка CSV данных и создание конфигураций для Dota 2",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Полный процесс: API + обработка конфигураций (как запуск без флагов)",
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
        "--period",
        default="auto",
        help=(
            "D2PT period для /api/heroes/stats (например: 8, patch). "
            "auto = выбирается по дате последнего Dota патча. По умолчанию: auto"
        ),
    )
    parser.add_argument(
        "--min-matches",
        type=int,
        default=20,
        help="Минимум матчей (min_matches) для /api/heroes/stats. По умолчанию: 20",
    )
    parser.add_argument(
        "--mmr",
        type=int,
        default=7000,
        help="MMR фильтр для /api/heroes/stats. По умолчанию: 7000",
    )

    args = parser.parse_args()

    QUIET_MODE = args.quiet
    DEBUG_MODE = args.debug
    if DEBUG_MODE:
        QUIET_MODE = False
    setup_logging(QUIET_MODE, DEBUG_MODE)

    if not check_core_dependencies():
        sys.exit(1)

    success_count = 0
    total_count = 0

    if args.config:
        total_count += 1
        if run_config_processing():
            success_count += 1
    elif args.all or not args.config:
        if not QUIET_MODE:
            logger.info("Запуск полного процесса (D2PT API + конфиги)...")

        period = args.period
        if isinstance(period, str) and period.lower() == "auto":
            try:
                from modules.utils.patch_period import choose_d2pt_period

                chosen, latest, age_days = choose_d2pt_period(threshold_days=8)
                period = chosen
                if latest is not None and age_days is not None:
                    user_print(
                        f"Auto period: последний патч {latest.patch_number} "
                        f"({age_days} дн. назад) -> period={period}"
                    )
                else:
                    user_print(
                        f"Auto period: не удалось определить патч -> period={period}"
                    )
            except Exception as e:
                user_print(f"Auto period: ошибка определения патча ({e}) -> period=8")
                period = "8"

        total_count += 1
        if run_api_scraping(period=period, min_matches=args.min_matches, mmr=args.mmr):
            success_count += 1
            total_count += 1
            if run_config_processing():
                success_count += 1
        else:
            user_print(
                "Пропуск создания конфигов: сначала нужны свежие данные с API "
                "(проверьте сеть или попробуйте позже)."
            )

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
