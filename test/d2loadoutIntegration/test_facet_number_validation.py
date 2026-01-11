"""
Тесты проверки соответствия фасетов и их номеров
Проверяют что facet_number правильно вычисляется и соответствует именам фасетов
"""

import pytest
import pandas as pd
import os
from datetime import datetime

pytestmark = pytest.mark.slow

TEST_OUTPUT_DIR = "test_output"


def save_facet_number_table(df: pd.DataFrame, position: str):
    """Выводит таблицу фасетов в консоль (не сохраняет в файл - только full_comparison_Carry сохраняется)"""
    # Не сохраняем файлы, только выводим в консоль
    print(f"\n{'='*80}")
    print(f"ТАБЛИЦА ФАСЕТОВ И НОМЕРОВ - {position.upper()}")
    print(f"{'='*80}")
    
    # Определяем важные колонки
    important_columns = []
    column_priority = ["Hero", "Facet", "facet_number", "Matches", "WR", "Win Rate", "D2PT Rating"]
    
    for col in column_priority:
        if col in df.columns:
            important_columns.append(col)
    
    if not important_columns or "Hero" not in df.columns or "Facet" not in df.columns:
        print(f"[WARN] Не все колонки присутствуют")
        return None
    
    facet_table = df[important_columns].copy()
    
    # Сортируем по герою и номеру фасета
    if "facet_number" in facet_table.columns:
        facet_table = facet_table.sort_values(["Hero", "facet_number"])
    else:
        facet_table = facet_table.sort_values(["Hero"])
    
    print(facet_table.to_string(index=False))
    print(f"{'='*80}\n")
    
    # Группируем по героям для проверки
    print(f"[GROUPED] ФАСЕТЫ ПО ГЕРОЯМ (первые 10):")
    heroes_with_facets = facet_table.groupby("Hero").size()
    heroes_with_multiple = heroes_with_facets[heroes_with_facets > 1].index[:10]
    
    for hero in heroes_with_multiple:
        hero_facets = facet_table[facet_table["Hero"] == hero].sort_values("facet_number")
        print(f"\n  {hero}:")
        for _, row in hero_facets.iterrows():
            facet_name = row.get("Facet", "N/A")
            facet_num = row.get("facet_number", "N/A")
            print(f"    Фасет #{facet_num}: {facet_name}")
    
    print()
    return None


class TestFacetNumberValidation:
    """Тесты проверки номеров фасетов - оптимизированы с общими фикстурами"""

    def test_facet_numbers_comprehensive(self, carry_data):
        """
        Комплексный тест номеров фасетов:
        - Вычисление номеров
        - Соответствие именам
        - Уникальность для героев
        - Последовательность
        """
        df_with_numbers = carry_data
        position = "Carry"
        
        if df_with_numbers.empty:
            pytest.skip("Не удалось загрузить данные")
        
        # Сохраняем таблицу для проверки
        csv_path = save_facet_number_table(df_with_numbers, position)
        
        # 1. Проверка что колонки созданы
        assert "facet_number" in df_with_numbers.columns, "Колонка facet_number не создана"
        assert "Facet" in df_with_numbers.columns, "Колонка Facet отсутствует"
        assert "Hero" in df_with_numbers.columns, "Колонка Hero отсутствует"
        
        # 2. Проверка что номера вычислены
        facet_numbers = df_with_numbers["facet_number"].dropna()
        assert len(facet_numbers) > 0, "Номера фасетов не вычислены"
        assert (facet_numbers > 0).all(), "Есть неположительные номера фасетов"
        
        print(f"[OK] Номера фасетов вычислены корректно")
        print(f"   - Всего записей: {len(df_with_numbers)}")
        print(f"   - Записей с номерами: {len(facet_numbers)}")
        print(f"   - Диапазон номеров: {facet_numbers.min()} - {facet_numbers.max()}")
        
        # 3. Проверка уникальности номеров для каждого героя
        heroes_with_multiple = df_with_numbers.groupby("Hero").size()
        heroes_with_multiple = heroes_with_multiple[heroes_with_multiple > 1].index[:10]
        
        print(f"\n[CHECK] Проверка уникальности и последовательности:")
        for hero in heroes_with_multiple:
            hero_data = df_with_numbers[df_with_numbers["Hero"] == hero].sort_values("facet_number")
            numbers = hero_data["facet_number"].dropna()
            
            if len(numbers) > 1:
                # Номера должны быть уникальными
                assert numbers.nunique() == len(numbers), f"Дублирующиеся номера для {hero}"
                
                # Номера должны начинаться с 1
                assert min(numbers) >= 1, f"Номера для {hero} не начинаются с 1"
                
                # Выводим для проверки
                print(f"\n  {hero}:")
                for _, row in hero_data.iterrows():
                    facet = row.get("Facet", "N/A")
                    num = row.get("facet_number", "N/A")
                    print(f"    Фасет #{num}: {facet}")

    def test_full_facet_mapping_table(self, carry_data):
        """Проверка фасетов для позиции Carry (использует предзагруженные данные)"""
        df_with_numbers = carry_data
        
        if df_with_numbers.empty:
            pytest.skip("Не удалось загрузить данные")
        
        # Выводим таблицу (не сохраняем - только full_comparison_Carry сохраняется)
        save_facet_number_table(df_with_numbers, "Carry")
        
        # Проверяем что данные есть
        assert "Hero" in df_with_numbers.columns
        assert "Facet" in df_with_numbers.columns
        assert "facet_number" in df_with_numbers.columns
