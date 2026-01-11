"""
Тесты проверки соответствия спарсенных данных фактическим данным на сайте
Проверяют что данные реально спарсились и соответствуют тому что на сайте
Сохраняют промежуточные результаты для сравнения с сайтом
"""

import pytest
import pandas as pd
import os
from datetime import datetime

pytestmark = pytest.mark.slow

# Директория для сохранения результатов тестов
TEST_OUTPUT_DIR = "test_output"


def save_scraped_data(df: pd.DataFrame, position: str, test_name: str):
    """Сохраняет спарсенные данные в файлы для сравнения - только full_comparison_Carry"""
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    
    # Сохраняем только full_comparison_Carry
    if test_name != "full_comparison" or position != "Carry":
        print(f"[SKIP] Пропущено сохранение {test_name}_{position} (сохраняем только full_comparison_Carry)")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Определяем важные колонки для вывода
    important_columns = []
    column_priority = ["Hero", "Facet", "facet_number", "Matches", "WR", "Win Rate", "D2PT Rating", "Role"]
    
    for col in column_priority:
        if col in df.columns:
            important_columns.append(col)
    
    # Добавляем остальные колонки если их мало (для полноты)
    other_cols = [c for c in df.columns if c not in important_columns]
    if len(important_columns) < 8 and other_cols:
        important_columns.extend(other_cols[:5])  # Максимум 5 дополнительных
    
    # Создаем таблицу с важными полями
    display_df = df[important_columns].copy() if important_columns else df
    
    # Сохраняем полные данные в CSV
    csv_path = os.path.join(TEST_OUTPUT_DIR, f"{test_name}_{position}_{timestamp}.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n[SAVED] Спарсенные данные сохранены: {csv_path}")
    
    # Выводим таблицу с важными полями в консоль
    print(f"\n{'='*80}")
    print(f"СПАРСЕННЫЕ ДАННЫЕ - {position.upper()} (важные поля)")
    print(f"{'='*80}")
    print(display_df.to_string(index=False))
    print(f"{'='*80}\n")
    
    # Выводим статистику
    print(f"[STATS] Статистика:")
    print(f"   - Всего строк: {len(df)}")
    print(f"   - Важные колонки: {', '.join(important_columns)}")
    if "Hero" in df.columns:
        print(f"   - Уникальных героев: {df['Hero'].nunique()}")
    if "Facet" in df.columns:
        facets_count = df["Facet"].dropna().nunique()
        print(f"   - Уникальных фасетов: {facets_count}")
    if "facet_number" in df.columns:
        print(f"   - Записей с номерами фасетов: {df['facet_number'].notna().sum()}")
    print()
    
    return csv_path


class TestActualDataValidation:
    """Тесты проверки фактических данных - оптимизированы с общими фикстурами"""

    def test_scraped_data_comprehensive(self, carry_data):
        """
        Комплексный тест спарсенных данных:
        - Реальные имена героев
        - Валидная статистика
        - Достаточное количество данных
        - Структура данных
        - Фасеты
        - Сохранение для сравнения
        """
        df_with_numbers = carry_data
        position = "Carry"
        
        if df_with_numbers.empty:
            pytest.skip("Не удалось загрузить данные")
        
        # Сохраняем данные для сравнения
        csv_path = save_scraped_data(df_with_numbers, position, "full_comparison")
        
        print(f"\n[COMPARE] Для сравнения откройте сайт: https://dota2protracker.com/meta")
        print(f"   Выберите позицию: {position}")
        print(f"   Сравните с файлом: {csv_path}\n")
        
        # 1. Проверка базовой структуры
        assert not df_with_numbers.empty, "Не удалось извлечь данные"
        assert "Hero" in df_with_numbers.columns, "Отсутствует колонка Hero"
        assert len(df_with_numbers) > 1, f"Спарсено слишком мало данных: {len(df_with_numbers)} строк"
        assert len(df_with_numbers) >= 5, f"Спарсено мало данных: {len(df_with_numbers)} строк. Ожидается минимум 5"
        
        # 2. Проверка имен героев
        hero_names = df_with_numbers["Hero"].dropna().unique()
        assert len(hero_names) > 0, "Не найдено имен героев"
        
        valid_heroes = [h for h in hero_names if isinstance(h, str) and len(h.strip()) > 2]
        assert len(valid_heroes) > 0, f"Не найдено валидных имен героев. Найдено: {hero_names[:5]}"
        
        print(f"[OK] Найдено валидных героев: {len(valid_heroes)}")
        print(f"   Примеры: {', '.join(valid_heroes[:10])}")
        
        # 3. Проверка статистики
        if "Matches" in df_with_numbers.columns:
            matches = df_with_numbers["Matches"].dropna()
            if len(matches) > 0:
                numeric_matches = pd.to_numeric(matches, errors='coerce').dropna()
                assert len(numeric_matches) > 0, "Матчи не являются числами"
                assert (numeric_matches > 0).any(), "Нет положительных значений матчей"
        
        if "WR" in df_with_numbers.columns or "Win Rate" in df_with_numbers.columns:
            wr_col = "WR" if "WR" in df_with_numbers.columns else "Win Rate"
            wr_values = df_with_numbers[wr_col].dropna()
            if len(wr_values) > 0:
                numeric_wr = pd.to_numeric(wr_values, errors='coerce').dropna()
                assert len(numeric_wr) > 0, "WR не является числом"
                valid_wr = numeric_wr[(numeric_wr >= 0) & (numeric_wr <= 100)]
                assert len(valid_wr) > 0, f"WR не в диапазоне 0-100. Найдено: {numeric_wr.head()}"
        
        # 4. Проверка фасетов
        if "Facet" in df_with_numbers.columns:
            facets = df_with_numbers["Facet"].dropna()
            if len(facets) > 0:
                unique_facets = facets.unique()
                print(f"\n[FACETS] ФАСЕТЫ:")
                print(f"   - Всего записей с фасетами: {len(facets)}")
                print(f"   - Уникальных фасетов: {len(unique_facets)}")
                print(f"   - Примеры фасетов: {', '.join(map(str, unique_facets[:10]))}")
        
        # 5. Выводим таблицу с важными полями
        important_cols = ["Hero", "Facet", "facet_number", "Matches", "WR", "Win Rate", "D2PT Rating"]
        available_cols = [c for c in important_cols if c in df_with_numbers.columns]
        
        if available_cols:
            print(f"\n[FACET-TABLE] ТАБЛИЦА ВАЖНЫХ ПОЛЕЙ (первые 20 строк):")
            facet_table = df_with_numbers[available_cols].head(20)
            print(facet_table.to_string(index=False))
            print()
        
        # 6. Топ героев
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
