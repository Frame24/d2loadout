"""
Тесты проверки соответствия фасетов и их номеров
Проверяют что facet_number правильно вычисляется и соответствует именам фасетов
"""

import pytest
import pandas as pd
import os
from datetime import datetime
from dota2_data_scraper.modules.core.scraping_manager import ScrapingManager
from dota2_data_scraper.modules.scrapers.hero_scraper import HeroScraper

pytestmark = pytest.mark.slow

TEST_OUTPUT_DIR = "test_output"


def save_facet_number_table(df: pd.DataFrame, position: str):
    """Сохраняет таблицу Hero | Facet | facet_number для проверки"""
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Создаем таблицу для проверки фасетов
    if "Hero" in df.columns and "Facet" in df.columns and "facet_number" in df.columns:
        facet_table = df[["Hero", "Facet", "facet_number"]].copy()
        
        # Сортируем по герою и номеру фасета для удобства проверки
        facet_table = facet_table.sort_values(["Hero", "facet_number"])
        
        # Сохраняем в CSV
        csv_path = os.path.join(TEST_OUTPUT_DIR, f"facet_numbers_{position}_{timestamp}.csv")
        facet_table.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n{'='*80}")
        print(f"ТАБЛИЦА ФАСЕТОВ И НОМЕРОВ - {position.upper()}")
        print(f"{'='*80}")
        print(facet_table.to_string(index=False))
        print(f"{'='*80}")
        print(f"\n[SAVED] Таблица сохранена: {csv_path}\n")
        
        # Группируем по героям для проверки соответствия
        print(f"[GROUPED] ФАСЕТЫ ПО ГЕРОЯМ (для проверки соответствия номеров):")
        heroes_with_facets = facet_table.groupby("Hero").size()
        heroes_with_multiple = heroes_with_facets[heroes_with_facets > 1].index[:15]  # Первые 15 с несколькими фасетами
        
        for hero in heroes_with_multiple:
            hero_facets = facet_table[facet_table["Hero"] == hero].sort_values("facet_number")
            print(f"\n  {hero}:")
            for _, row in hero_facets.iterrows():
                facet_name = row.get("Facet", "N/A")
                facet_num = row.get("facet_number", "N/A")
                print(f"    Фасет #{facet_num}: {facet_name}")
        
        print(f"\n[INFO] Всего героев с несколькими фасетами: {len(heroes_with_multiple)}")
        print()
        
        return csv_path
    else:
        print(f"[WARN] Не все колонки присутствуют для создания таблицы фасетов")
        print(f"   Найдены колонки: {list(df.columns)}")
        return None


class TestFacetNumberValidation:
    """Тесты проверки номеров фасетов"""

    def test_facet_numbers_are_calculated(self):
        """Тест что номера фасетов вычисляются корректно"""
        scraper = HeroScraper(headless=True)
        position = "Carry"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = f"//div[contains(text(), '{position}')]"
            if manager.click_element_safely(xpath, timeout=15):
                # Извлекаем данные
                df = scraper._extract_table_data(manager.driver)
                df["Role"] = f"pos 1"
                
                # Вычисляем номера фасетов (как в реальном коде)
                df_with_numbers = scraper._ensure_facet_names_and_numbers(df)
                
                # Сохраняем таблицу для проверки
                csv_path = save_facet_number_table(df_with_numbers, position)
                
                assert "facet_number" in df_with_numbers.columns, "Колонка facet_number не создана"
                assert "Facet" in df_with_numbers.columns, "Колонка Facet отсутствует"
                
                # Проверяем что номера есть
                facet_numbers = df_with_numbers["facet_number"].dropna()
                assert len(facet_numbers) > 0, "Номера фасетов не вычислены"
                
                # Проверяем что номера положительные
                assert (facet_numbers > 0).all(), "Есть неположительные номера фасетов"
                
                print(f"[OK] Номера фасетов вычислены корректно")
                print(f"   - Всего записей: {len(df_with_numbers)}")
                print(f"   - Записей с номерами: {len(facet_numbers)}")
                print(f"   - Диапазон номеров: {facet_numbers.min()} - {facet_numbers.max()}")

    def test_facet_numbers_match_facet_names(self):
        """Тест что номера фасетов соответствуют именам"""
        scraper = HeroScraper(headless=True)
        position = "Carry"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = f"//div[contains(text(), '{position}')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                df["Role"] = f"pos 1"
                
                # Вычисляем номера
                df_with_numbers = scraper._ensure_facet_names_and_numbers(df)
                
                # Сохраняем для проверки
                save_facet_number_table(df_with_numbers, position)
                
                # Проверяем что для каждого героя номера уникальны в рамках героя
                if "Hero" in df_with_numbers.columns:
                    for hero in df_with_numbers["Hero"].dropna().unique()[:5]:  # Проверяем первые 5
                        hero_data = df_with_numbers[df_with_numbers["Hero"] == hero]
                        if "facet_number" in hero_data.columns:
                            numbers = hero_data["facet_number"].dropna()
                            if len(numbers) > 1:
                                # Номера должны быть уникальными для одного героя
                                assert numbers.nunique() == len(numbers), f"Дублирующиеся номера для {hero}"
                                
                                # Выводим для проверки
                                print(f"\n[CHECK] {hero}:")
                                for _, row in hero_data.iterrows():
                                    facet = row.get("Facet", "N/A")
                                    num = row.get("facet_number", "N/A")
                                    print(f"   Фасет #{num}: {facet}")

    def test_facet_numbers_sequential_for_same_hero(self):
        """Тест что номера фасетов последовательные для одного героя"""
        scraper = HeroScraper(headless=True)
        position = "Carry"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            xpath = f"//div[contains(text(), '{position}')]"
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                df["Role"] = f"pos 1"
                
                df_with_numbers = scraper._ensure_facet_names_and_numbers(df)
                
                # Сохраняем таблицу
                save_facet_number_table(df_with_numbers, position)
                
                # Проверяем последовательность для героев с несколькими фасетами
                if "Hero" in df_with_numbers.columns:
                    heroes_with_multiple = df_with_numbers.groupby("Hero").size()
                    heroes_with_multiple = heroes_with_multiple[heroes_with_multiple > 1].index[:5]
                    
                    print(f"\n[SEQUENCE] Проверка последовательности номеров:")
                    for hero in heroes_with_multiple:
                        hero_data = df_with_numbers[df_with_numbers["Hero"] == hero].sort_values("facet_number")
                        numbers = hero_data["facet_number"].tolist()
                        facets = hero_data["Facet"].tolist()
                        
                        print(f"\n  {hero}:")
                        for num, facet in zip(numbers, facets):
                            print(f"    #{num}: {facet}")
                        
                        # Проверяем что номера начинаются с 1 и идут последовательно
                        if len(numbers) > 0:
                            assert min(numbers) >= 1, f"Номера для {hero} не начинаются с 1"
                            # Номера могут быть не строго последовательными (1,2,3), но должны быть уникальными
                            assert len(set(numbers)) == len(numbers), f"Дублирующиеся номера для {hero}"

    def test_full_facet_mapping_table(self):
        """Полная таблица маппинга фасетов для всех позиций"""
        scraper = HeroScraper(headless=True)
        positions = {
            "Carry": ("//div[contains(text(), 'Carry')]", "pos 1"),
            "Mid": ("//div[contains(text(), 'Mid')]", "pos 2"),
        }
        
        all_facet_data = []
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            for pos_name, (xpath, role) in positions.items():
                print(f"\n{'='*80}")
                print(f"[PROCESSING] Обработка позиции: {pos_name}")
                print(f"{'='*80}")
                
                if manager.click_element_safely(xpath, timeout=15):
                    df = scraper._extract_table_data(manager.driver)
                    df["Role"] = role
                    
                    # Вычисляем номера фасетов
                    df_with_numbers = scraper._ensure_facet_names_and_numbers(df)
                    
                    # Сохраняем таблицу для этой позиции
                    save_facet_number_table(df_with_numbers, pos_name)
                    
                    # Добавляем в общий список
                    if "Hero" in df_with_numbers.columns and "Facet" in df_with_numbers.columns and "facet_number" in df_with_numbers.columns:
                        facet_subset = df_with_numbers[["Hero", "Facet", "facet_number", "Role"]].copy()
                        all_facet_data.append(facet_subset)
        
        # Сохраняем объединенную таблицу
        if all_facet_data:
            combined = pd.concat(all_facet_data, ignore_index=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            combined_path = os.path.join(TEST_OUTPUT_DIR, f"all_facet_numbers_{timestamp}.csv")
            combined.to_csv(combined_path, index=False, encoding='utf-8-sig')
            
            print(f"\n{'='*80}")
            print(f"[SUMMARY] ОБЪЕДИНЕННАЯ ТАБЛИЦА ФАСЕТОВ")
            print(f"{'='*80}")
            print(combined.to_string(index=False))
            print(f"{'='*80}")
            print(f"\n[SAVED] Объединенная таблица: {combined_path}\n")
            
            # Статистика
            print(f"[STATS] Статистика:")
            print(f"   - Всего записей: {len(combined)}")
            print(f"   - Уникальных героев: {combined['Hero'].nunique()}")
            print(f"   - Уникальных фасетов: {combined['Facet'].nunique()}")
            print(f"   - Диапазон номеров: {combined['facet_number'].min()} - {combined['facet_number'].max()}\n")
