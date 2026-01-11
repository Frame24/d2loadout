"""
Интеграционные тесты для проверки фактической работы скрапера
Проверяют, что скрапер может работать с реальным сайтом
Оптимизированы с общими фикстурами
"""

import pytest
import pandas as pd
from bs4 import BeautifulSoup

pytestmark = pytest.mark.slow


class TestScraperIntegration:
    """Тесты фактической работы скрапера с сайтом - оптимизированы"""

    def test_scraper_basic_functionality(self, browser_manager, scraper):
        """
        Комплексный тест базовой функциональности скрапера:
        - Загрузка страницы
        - Наличие элементов таблицы
        - Кнопки позиций
        - Клик по позиции
        - Извлечение данных
        """
        # 1. Проверка загрузки страницы
        page_source = browser_manager.get_page_source()
        assert len(page_source) > 0, "Страница не загрузилась"
        assert "dota2protracker" in page_source.lower() or len(page_source) > 1000, "Неверная страница"
        
        # 2. Проверка элементов таблицы
        soup = BeautifulSoup(page_source, "html.parser")
        table_rows = soup.find_all("div", class_="grid", style=True)
        assert len(table_rows) > 0, "Не найдены элементы таблицы с классом 'grid'"
        
        # 3. Проверка кнопок позиций
        positions = ["Carry", "Mid", "Off", "Pos 4", "Pos 5"]
        found_positions = [pos for pos in positions if pos.lower() in page_source.lower()]
        assert len(found_positions) > 0, f"Не найдены кнопки позиций. Найдено: {found_positions}"
        
        # 4. Проверка клика по позиции и извлечения данных
        xpath = "//div[contains(text(), 'Carry')]"
        result = browser_manager.click_element_safely(xpath, timeout=15)
        assert result is True, f"Не удалось кликнуть по кнопке позиции {xpath}"
        
        # 5. Проверка извлечения данных
        df = scraper._extract_table_data(browser_manager.driver)
        assert not df.empty, "Не удалось извлечь данные"
        assert "Hero" in df.columns, "Отсутствует колонка Hero"
        
        hero_names = df["Hero"].dropna()
        assert len(hero_names) > 0, "Не найдено имен героев"
        
        # 6. Проверка структуры таблицы
        page_source_after = browser_manager.get_page_source()
        soup_after = BeautifulSoup(page_source_after, "html.parser")
        table_rows_after = soup_after.find_all("div", class_="grid", style=True)
        assert len(table_rows_after) > 1, "Не найдено достаточно строк таблицы"
        
        if table_rows_after:
            first_row = table_rows_after[0]
            cols = first_row.find_all("div", recursive=False)
            assert len(cols) > 0, "Строка таблицы не содержит колонок"

    def test_html_structure_and_dataframe(self, browser_manager, scraper):
        """
        Комплексный тест структуры HTML и DataFrame:
        - HTML структура содержит необходимые элементы
        - DataFrame содержит необходимые колонки
        - Селектор периода существует
        - Кнопка переключения фасетов
        """
        page_source = browser_manager.get_page_source()
        soup = BeautifulSoup(page_source, "html.parser")
        
        # Проверка HTML структуры
        required_elements = {
            "grid_divs": len(soup.find_all("div", class_="grid")) > 0,
            "has_images": len(soup.find_all("img")) > 0,
        }
        failed_checks = [k for k, v in required_elements.items() if not v]
        assert len(failed_checks) == 0, f"Отсутствуют необходимые элементы: {failed_checks}"
        
        # Проверка кнопки переключения фасетов
        possible_selectors = ['button[role="switch"]', '[role="switch"]']
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
        
        # Проверка селектора периода
        select_elements = soup.find_all("select")
        option_elements = soup.find_all("option")
        has_period_selector = len(select_elements) > 0 or len(option_elements) > 0
        assert has_period_selector, "Селектор периода не найден на странице"
        
        # Проверка DataFrame
        xpath = "//div[contains(text(), 'Carry')]"
        if browser_manager.click_element_safely(xpath, timeout=15):
            df = scraper._extract_table_data(browser_manager.driver)
            
            if not df.empty:
                # Проверяем обязательные колонки
                required_columns = ["Hero", "Matches", "WR"]
                existing_columns = set(df.columns)
                missing_columns = [col for col in required_columns if col not in existing_columns]
                assert len(missing_columns) == 0, f"Отсутствуют колонки: {missing_columns}"
                
                # Проверяем что есть данные
                hero_names = df["Hero"].dropna()
                assert len(hero_names) > 0, "Не найдено имен героев"
                
                # Проверяем статистику
                if "Matches" in df.columns:
                    matches = df["Matches"].dropna()
                    assert len(matches) > 0, "Не найдено данных о матчах"
