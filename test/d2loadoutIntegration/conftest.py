"""
Общие фикстуры для интеграционных тестов
Переиспользуют браузер и данные для ускорения тестов
"""

import pytest
import pandas as pd
from dota2_data_scraper.modules.core.scraping_manager import ScrapingManager
from dota2_data_scraper.modules.scrapers.hero_scraper import HeroScraper
from dota2_data_scraper.modules.utils.facet_api_parser import FacetAPIParser


@pytest.fixture(scope="session")
def dotabuff_mapping():
    """Маппинг фасетов из Dotabuff - загружается один раз на всю сессию"""
    parser = FacetAPIParser()
    try:
        # Используем minimize_window=True для скрытия окна
        with ScrapingManager(headless=False, minimize_window=True) as manager:
            mapping = parser._try_dotabuff_facets(manager)
            if mapping and len(mapping) > 0:
                print(f"[OK] Dotabuff маппинг загружен: {len(mapping)} героев")
                return mapping
    except Exception as e:
        print(f"[WARN] Не удалось загрузить Dotabuff маппинг: {e}")
    
    return {}


@pytest.fixture(scope="class")
def browser_manager():
    """Общий браузер для всех тестов класса"""
    with ScrapingManager(headless=True) as manager:
        manager.navigate_to_page("https://dota2protracker.com/meta")
        yield manager


@pytest.fixture(scope="class")
def scraper(dotabuff_mapping):
    """Общий скрапер для всех тестов класса с предзагруженным Dotabuff маппингом"""
    scraper = HeroScraper(headless=True)
    # Предзагружаем маппинг, чтобы не открывать Dotabuff каждый раз
    scraper.facet_parser.hero_facets_cache = dotabuff_mapping
    return scraper


@pytest.fixture(scope="class")
def carry_data(browser_manager, scraper):
    """Данные позиции Carry - загружаются один раз для класса"""
    position = "Carry"
    xpath = f"//div[contains(text(), '{position}')]"
    
    if browser_manager.click_element_safely(xpath, timeout=15):
        df = scraper._extract_table_data(browser_manager.driver)
        df["Role"] = "pos 1"
        
        # Вычисляем номера фасетов (как в реальном коде)
        # Маппинг уже предзагружен, Dotabuff не откроется
        df_with_numbers = scraper._ensure_facet_names_and_numbers(df)
        return df_with_numbers
    
    return pd.DataFrame()
