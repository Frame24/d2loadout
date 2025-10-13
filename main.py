import sys


def _run():
    from dota2_data_scraper.main import main as _entry

    sys.exit(_entry())


if __name__ == "__main__":
    _run()


