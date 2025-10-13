import sys
import os


def _run():
    # Добавляем папку с пакетами в sys.path, чтобы сработали импорты вида `from modules...`
    base_dir = os.path.dirname(__file__)
    pkg_dir = os.path.join(base_dir, "dota2_data_scraper")
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    from dota2_data_scraper.main import main as _entry

    sys.exit(_entry())


if __name__ == "__main__":
    _run()


