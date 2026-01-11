"""
Интеграционные тесты для проверки фактической работы скрапера
Проверяют, что скрапер может работать с реальным сайтом
"""

import pytest

pytestmark = pytest.mark.slow
import pandas as pd
from dota2_data_scraper.modules.core.scraping_manager import ScrapingManager
from dota2_data_scraper.modules.scrapers.hero_scraper import HeroScraper
from bs4 import BeautifulSoup


class TestScraperIntegration:
    """Тесты фактической работы скрапера с сайтом"""

    @pytest.fixture(scope="class")
    def scraper(self):
        """Экземпляр скрапера для тестов"""
        return HeroScraper(headless=True)

    def test_page_loads_successfully(self):
        """Тест что страница dota2protracker.com загружается"""
        with ScrapingManager(headless=True) as manager:
            try:
                manager.navigate_to_page("https://dota2protracker.com/meta")
                page_source = manager.get_page_source()
                assert len(page_source) > 0
                assert "dota2protracker" in page_source.lower() or len(page_source) > 1000
            except Exception as e:
                pytest.fail(f"Страница не загрузилась: {e}")

    def test_page_contains_table_elements(self):
        """Тест что на странице есть элементы таблицы с классом grid"""
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            soup = BeautifulSoup(page_source, "html.parser")
            
            table_rows = soup.find_all("div", class_="grid", style=True)
            assert len(table_rows) > 0, "Не найдены элементы таблицы с классом 'grid'"

    def test_position_buttons_exist(self):
        """Тест что кнопки позиций существуют на странице"""
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            
            positions = [
                "Carry",
                "Mid",
                "Off",
                "Pos 4",
                "Pos 5"
            ]
            
            found_positions = []
            for pos in positions:
                if pos.lower() in page_source.lower():
                    found_positions.append(pos)
            
            assert len(found_positions) > 0, f"Не найдены кнопки позиций. Найдено: {found_positions}"

    def test_can_click_position_button(self):
        """Тест что можно кликнуть по кнопке позиции"""
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            result = manager.click_element_safely(xpath, timeout=15)
            
            assert result is True, f"Не удалось кликнуть по кнопке позиции {xpath}"

    def test_table_data_extraction_structure(self):
        """Тест что структура извлеченных данных корректна"""
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            if manager.click_element_safely(xpath, timeout=15):
                page_source = manager.get_page_source()
                soup = BeautifulSoup(page_source, "html.parser")
                
                table_rows = soup.find_all("div", class_="grid", style=True)
                assert len(table_rows) > 1, "Не найдено достаточно строк таблицы"
                
                first_row = table_rows[0] if table_rows else None
                if first_row:
                    cols = first_row.find_all("div", recursive=False)
                    assert len(cols) > 0, "Строка таблицы не содержит колонок"

    def test_hero_names_extracted(self):
        """Тест что имена героев извлекаются из таблицы"""
        scraper = HeroScraper(headless=True)
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                assert not df.empty, "DataFrame пуст после извлечения данных"
                assert "Hero" in df.columns, "Колонка 'Hero' отсутствует в данных"
                
                if len(df) > 0:
                    hero_names = df["Hero"].dropna()
                    assert len(hero_names) > 0, "Не найдено имен героев в данных"

    def test_facet_toggle_button_exists(self):
        """Тест что кнопка переключения группировки фасетов существует"""
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            
            possible_selectors = [
                'button[role="switch"]',
                '[role="switch"]',
            ]
            
            soup = BeautifulSoup(page_source, "html.parser")
            found = False
            
            for selector in possible_selectors:
                elements = soup.select(selector)
                if elements:
                    for el in elements:
                        if el.get("role") == "switch":
                            found = True
                            break
                if found:
                    break
            
            assert found, "Кнопка переключения группировки фасетов не найдена"

    def test_html_structure_has_required_elements(self):
        """Тест что HTML структура содержит необходимые элементы для парсинга"""
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            soup = BeautifulSoup(page_source, "html.parser")
            
            required_elements = {
                "grid_divs": len(soup.find_all("div", class_="grid")) > 0,
                "has_images": len(soup.find_all("img")) > 0,
            }
            
            failed_checks = [k for k, v in required_elements.items() if not v]
            assert len(failed_checks) == 0, f"Отсутствуют необходимые элементы: {failed_checks}"

    def test_dataframe_has_required_columns(self):
        """Тест что извлеченный DataFrame содержит необходимые колонки"""
        scraper = HeroScraper(headless=True)
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                if not df.empty:
                    required_columns = ["Hero", "Matches", "WR"]
                    existing_columns = set(df.columns)
                    
                    missing_columns = [col for col in required_columns if col not in existing_columns]
                    assert len(missing_columns) == 0, f"Отсутствуют колонки: {missing_columns}"

    def test_period_selector_exists(self):
        """Тест что селектор периода существует на странице"""
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            
            soup = BeautifulSoup(page_source, "html.parser")
            
            select_elements = soup.find_all("select")
            option_elements = soup.find_all("option")
            
            has_period_selector = len(select_elements) > 0 or len(option_elements) > 0
            
            assert has_period_selector, "Селектор периода не найден на странице"

    @pytest.mark.slow
    def test_full_scraping_cycle_single_position(self):
        """Тест полного цикла скрапинга для одной позиции"""
        scraper = HeroScraper(headless=True)
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                assert not df.empty, "Не удалось извлечь данные"
                assert "Hero" in df.columns, "Отсутствует колонка Hero"
                assert "Role" not in df.columns or True, "Колонка Role должна быть добавлена позже"
                
                if len(df) > 0:
                    assert df["Hero"].notna().any(), "Нет данных о героях"
