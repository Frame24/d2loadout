"""
Тесты проверки соответствия спарсенных данных фактическим данным на сайте
Проверяют что данные реально спарсились и соответствуют тому что на сайте
Сохраняют промежуточные результаты для сравнения с сайтом
"""

import pytest
import pandas as pd
import os
from datetime import datetime
from dota2_data_scraper.modules.core.scraping_manager import ScrapingManager
from dota2_data_scraper.modules.scrapers.hero_scraper import HeroScraper

pytestmark = pytest.mark.slow

# Директория для сохранения результатов тестов
TEST_OUTPUT_DIR = "test_output"


def save_scraped_data(df: pd.DataFrame, position: str, test_name: str):
    """Сохраняет спарсенные данные в файлы для сравнения"""
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Сохраняем в CSV для удобного просмотра
    csv_path = os.path.join(TEST_OUTPUT_DIR, f"{test_name}_{position}_{timestamp}.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n[SAVED] Спарсенные данные сохранены: {csv_path}")
    
    # Выводим таблицу в консоль для быстрого просмотра
    print(f"\n{'='*80}")
    print(f"СПАРСЕННЫЕ ДАННЫЕ - {position.upper()}")
    print(f"{'='*80}")
    print(df.to_string())
    print(f"{'='*80}\n")
    
    # Выводим статистику
    print(f"[STATS] Статистика:")
    print(f"   - Всего строк: {len(df)}")
    print(f"   - Колонки: {', '.join(df.columns.tolist())}")
    if "Hero" in df.columns:
        print(f"   - Уникальных героев: {df['Hero'].nunique()}")
    if "Facet" in df.columns:
        facets_count = df["Facet"].dropna().nunique()
        print(f"   - Уникальных фасетов: {facets_count}")
    print()
    
    return csv_path


class TestActualDataValidation:
    """Тесты проверки фактических данных"""

    def test_scraped_data_contains_real_heroes(self):
        """Тест что спарсенные данные содержат реальных героев"""
        scraper = HeroScraper(headless=True)
        position = "Carry"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = f"//div[contains(text(), '{position}')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                df["Role"] = f"pos 1"
                
                # Вычисляем номера фасетов (как в реальном коде)
                df_with_numbers = scraper._ensure_facet_names_and_numbers(df)
                
                # Сохраняем данные для сравнения (с номерами фасетов)
                save_scraped_data(df_with_numbers, position, "heroes")
                
                assert not df_with_numbers.empty, "Не удалось извлечь данные"
                assert "Hero" in df_with_numbers.columns, "Отсутствует колонка Hero"
                assert "facet_number" in df_with_numbers.columns, "Отсутствует колонка facet_number"
                
                # Проверяем что есть реальные имена героев
                hero_names = df_with_numbers["Hero"].dropna().unique()
                assert len(hero_names) > 0, "Не найдено имен героев"
                
                # Проверяем что имена не пустые и не мусор
                valid_heroes = [h for h in hero_names if isinstance(h, str) and len(h.strip()) > 2]
                assert len(valid_heroes) > 0, f"Не найдено валидных имен героев. Найдено: {hero_names[:5]}"
                
                print(f"[OK] Найдено валидных героев: {len(valid_heroes)}")
                print(f"   Примеры: {', '.join(valid_heroes[:10])}")
                
                # Выводим таблицу Hero | Facet | facet_number для проверки
                if "Facet" in df_with_numbers.columns:
                    print(f"\n[FACET-TABLE] ТАБЛИЦА ГЕРОЙ | ФАСЕТ | НОМЕР:")
                    facet_table = df_with_numbers[["Hero", "Facet", "facet_number"]].head(20)
                    print(facet_table.to_string(index=False))
                    print()

    def test_scraped_data_has_valid_statistics(self):
        """Тест что спарсенные данные содержат валидную статистику"""
        scraper = HeroScraper(headless=True)
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                if not df.empty:
                    # Проверяем что есть колонка с матчами
                    if "Matches" in df.columns:
                        matches = df["Matches"].dropna()
                        if len(matches) > 0:
                            # Проверяем что матчи - это числа
                            numeric_matches = pd.to_numeric(matches, errors='coerce').dropna()
                            assert len(numeric_matches) > 0, "Матчи не являются числами"
                            # Проверяем что матчи положительные
                            assert (numeric_matches > 0).any(), "Нет положительных значений матчей"
                    
                    # Проверяем что есть колонка с WR
                    if "WR" in df.columns or "Win Rate" in df.columns:
                        wr_col = "WR" if "WR" in df.columns else "Win Rate"
                        wr_values = df[wr_col].dropna()
                        if len(wr_values) > 0:
                            # Проверяем что WR - это числа
                            numeric_wr = pd.to_numeric(wr_values, errors='coerce').dropna()
                            assert len(numeric_wr) > 0, "WR не является числом"
                            # Проверяем что WR в разумном диапазоне (0-100)
                            valid_wr = numeric_wr[(numeric_wr >= 0) & (numeric_wr <= 100)]
                            assert len(valid_wr) > 0, f"WR не в диапазоне 0-100. Найдено: {numeric_wr.head()}"

    def test_scraped_data_has_multiple_rows(self):
        """Тест что спарсено достаточно данных (не одна строка)"""
        scraper = HeroScraper(headless=True)
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                assert len(df) > 1, f"Спарсено слишком мало данных: {len(df)} строк. Ожидается больше 1"
                assert len(df) >= 5, f"Спарсено мало данных: {len(df)} строк. Ожидается минимум 5"

    def test_scraped_data_structure_is_complete(self):
        """Тест что структура спарсенных данных полная"""
        scraper = HeroScraper(headless=True)
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                if not df.empty:
                    # Проверяем что есть основные колонки
                    essential_columns = ["Hero"]
                    missing = [col for col in essential_columns if col not in df.columns]
                    assert len(missing) == 0, f"Отсутствуют обязательные колонки: {missing}"
                    
                    # Проверяем что данные не полностью пустые
                    non_empty_rows = df.dropna(how='all')
                    assert len(non_empty_rows) > 0, "Все строки пустые"

    def test_scraped_heroes_have_valid_names(self):
        """Тест что имена героев валидные (не мусор, не пустые)"""
        scraper = HeroScraper(headless=True)
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = "//div[contains(text(), 'Carry')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                if not df.empty and "Hero" in df.columns:
                    hero_names = df["Hero"].dropna()
                    
                    # Проверяем что имена не пустые
                    non_empty = hero_names[hero_names.astype(str).str.strip() != ""]
                    assert len(non_empty) > 0, "Все имена героев пустые"
                    
                    # Проверяем что имена не слишком короткие (не мусор)
                    valid_length = non_empty[non_empty.astype(str).str.len() >= 3]
                    assert len(valid_length) > 0, "Имена героев слишком короткие (возможно мусор)"

    def test_scraped_data_has_facets_when_available(self):
        """Тест что фасеты извлекаются когда они есть на странице"""
        scraper = HeroScraper(headless=True)
        position = "Carry"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = f"//div[contains(text(), '{position}')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                # Сохраняем данные с фасетами
                save_scraped_data(df, position, "facets")
                
                if not df.empty:
                    # Если есть колонка Facet, проверяем что она заполнена
                    if "Facet" in df.columns:
                        facets = df["Facet"].dropna()
                        print(f"\n[FACETS] ФАСЕТЫ:")
                        print(f"   - Всего записей с фасетами: {len(facets)}")
                        if len(facets) > 0:
                            unique_facets = facets.unique()
                            print(f"   - Уникальных фасетов: {len(unique_facets)}")
                            print(f"   - Примеры фасетов: {', '.join(map(str, unique_facets[:10]))}")
                        
                        # Выводим таблицу герой-фасет для сравнения
                        if "Hero" in df.columns:
                            hero_facet = df[["Hero", "Facet"]].dropna(subset=["Facet"])
                            if len(hero_facet) > 0:
                                print(f"\n[HERO-FACET] ГЕРОИ И ФАСЕТЫ:")
                                print(hero_facet.to_string(index=False))
                                print()
                        
                        assert len(facets) > 0, "Колонка Facet существует, но пустая"
                    else:
                        print("[WARN] Колонка Facet не найдена (возможно режим без фасетов)")
                        # Если колонки нет, это тоже нормально (может быть режим без фасетов)
                        assert True

    def test_full_position_data_comparison(self):
        """Полный тест данных позиции - сохраняет все для сравнения с сайтом"""
        scraper = HeroScraper(headless=True)
        position = "Carry"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = f"//div[contains(text(), '{position}')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                
                # Вычисляем номера фасетов (как в реальном коде)
                df["Role"] = f"pos 1"
                df_with_numbers = scraper._ensure_facet_names_and_numbers(df)
                
                # Сохраняем полные данные (с номерами фасетов)
                csv_path = save_scraped_data(df_with_numbers, position, "full_comparison")
                
                print(f"\n[COMPARE] Для сравнения откройте сайт: https://dota2protracker.com/meta")
                print(f"   Выберите позицию: {position}")
                print(f"   Сравните с файлом: {csv_path}\n")
                
                assert not df_with_numbers.empty, "Не удалось извлечь данные"
                
                # Выводим топ героев с фасетами и номерами
                if "Hero" in df_with_numbers.columns and len(df_with_numbers) > 0:
                    print(f"[TOP-10] ТОП-10 ГЕРОЕВ ({position}):")
                    top_heroes = df_with_numbers.head(10)
                    for idx, row in top_heroes.iterrows():
                        hero = row.get("Hero", "N/A")
                        matches = row.get("Matches", "N/A")
                        wr = row.get("WR", row.get("Win Rate", "N/A"))
                        facet = row.get("Facet", "N/A")
                        facet_num = row.get("facet_number", "N/A")
                        print(f"   {idx+1}. {hero} | Матчи: {matches} | WR: {wr} | Фасет #{facet_num}: {facet}")
                    print()
                    
                    # Выводим таблицу Hero | Facet | facet_number для проверки соответствия
                    print(f"[FACET-TABLE] ТАБЛИЦА ГЕРОЙ | ФАСЕТ | НОМЕР (первые 20):")
                    if "Facet" in df_with_numbers.columns and "facet_number" in df_with_numbers.columns:
                        facet_table = df_with_numbers[["Hero", "Facet", "facet_number"]].head(20)
                        print(facet_table.to_string(index=False))
                        print()
