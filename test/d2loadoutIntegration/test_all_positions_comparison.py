"""
Тест для сравнения данных всех позиций с сайтом
Сохраняет данные всех позиций для ручного сравнения
"""

import pytest
import pandas as pd
import os
from dota2_data_scraper.modules.core.scraping_manager import ScrapingManager
from dota2_data_scraper.modules.scrapers.hero_scraper import HeroScraper

pytestmark = pytest.mark.slow

TEST_OUTPUT_DIR = "test_output"


def save_position_data(df: pd.DataFrame, position: str):
    """Сохраняет данные позиции"""
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(TEST_OUTPUT_DIR, f"position_{position.replace(' ', '_')}_{timestamp}.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    return csv_path


@pytest.mark.slow
def test_all_positions_data_extraction():
    """Извлекает данные всех позиций для сравнения с сайтом"""
    scraper = HeroScraper(headless=True)
    positions = {
        "Carry": "//div[contains(text(), 'Carry')]",
        "Mid": "//div[contains(text(), 'Mid')]",
        "Offlane": "//div[contains(text(), 'Off')]",
        "Pos 4": "//div[contains(text(), 'Pos 4')]",
        "Pos 5": "//div[contains(text(), 'Pos 5')]",
    }
    
    all_data = {}
    
    with ScrapingManager(headless=True) as manager:
        manager.navigate_to_page("https://dota2protracker.com/meta")
        
        for pos_name, xpath in positions.items():
            print(f"\n{'='*80}")
            print(f"[PROCESSING] ОБРАБОТКА ПОЗИЦИИ: {pos_name}")
            print(f"{'='*80}")
            
            if manager.click_element_safely(xpath, timeout=15):
                df = scraper._extract_table_data(manager.driver)
                df["Role"] = f"pos {pos_name.split()[-1]}" if pos_name.startswith("Pos") else f"pos {pos_name.split()[-1] if pos_name.split()[-1].isdigit() else {'Carry': '1', 'Mid': '2', 'Offlane': '3'}.get(pos_name, '?')}"
                
                # Сохраняем данные
                csv_path = save_position_data(df, pos_name)
                all_data[pos_name] = df
                
                print(f"[OK] Позиция {pos_name}:")
                print(f"   - Строк: {len(df)}")
                print(f"   - Колонки: {', '.join(df.columns.tolist())}")
                if "Hero" in df.columns:
                    print(f"   - Героев: {df['Hero'].nunique()}")
                if "Facet" in df.columns:
                    facets = df["Facet"].dropna()
                    print(f"   - Записей с фасетами: {len(facets)}")
                print(f"   - Сохранено: {csv_path}")
                
                # Выводим топ-5 для быстрой проверки
                if len(df) > 0:
                    print(f"\n   ТОП-5:")
                    top = df.head(5)
                    for idx, row in top.iterrows():
                        hero = row.get("Hero", "N/A")
                        matches = row.get("Matches", "N/A")
                        wr = row.get("WR", row.get("Win Rate", "N/A"))
                        print(f"      {idx+1}. {hero} | {matches} матчей | WR: {wr}")
            else:
                print(f"[ERROR] Не удалось кликнуть по позиции {pos_name}")
    
    # Сохраняем объединенные данные
    if all_data:
        combined_df = pd.concat(all_data.values(), ignore_index=True)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_path = os.path.join(TEST_OUTPUT_DIR, f"all_positions_{timestamp}.csv")
        combined_df.to_csv(combined_path, index=False, encoding='utf-8-sig')
        
        print(f"\n{'='*80}")
        print(f"[SUMMARY] ИТОГОВАЯ СТАТИСТИКА")
        print(f"{'='*80}")
        print(f"   - Всего позиций обработано: {len(all_data)}")
        print(f"   - Всего строк: {len(combined_df)}")
        print(f"   - Уникальных героев: {combined_df['Hero'].nunique() if 'Hero' in combined_df.columns else 'N/A'}")
        print(f"   - Объединенный файл: {combined_path}")
        print(f"\n[COMPARE] Для сравнения откройте: https://dota2protracker.com/meta")
        print(f"{'='*80}\n")
        
        assert len(all_data) > 0, "Не удалось извлечь данные ни для одной позиции"
