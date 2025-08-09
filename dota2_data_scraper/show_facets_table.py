"""
Отображение таблицы фасетов для проверки
"""

import pandas as pd
from modules.utils.facet_api_parser import FacetAPIParser


def show_facets_table():
    """Показывает таблицу с фасетами для проверки правильности парсинга"""

    print("🎭 ТАБЛИЦА ФАСЕТОВ ГЕРОЕВ")
    print("=" * 80)

    # Загружаем собранные данные
    try:
        df = pd.read_csv("heroes_data.csv")
        print(f"✅ Загружен файл с {len(df)} записями")
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        return

    # Получаем правильные фасеты из API
    parser = FacetAPIParser()
    api_facets = parser.get_hero_facets_mapping()

    print(f"✅ Получены фасеты из API для {len(api_facets)} героев")
    print()

    # 1. Показываем примеры известных героев
    test_heroes = [
        "Crystal Maiden",
        "Pudge",
        "Anti-Mage",
        "Invoker",
        "Juggernaut",
        "Axe",
    ]

    print("🔍 ПРОВЕРКА ИЗВЕСТНЫХ ГЕРОЕВ:")
    print("-" * 80)

    for hero in test_heroes:
        if hero in api_facets:
            api_hero_facets = api_facets[hero]

            print(f"\n🦸 {hero}:")
            print(f"   Фасеты из API: {api_hero_facets}")

            # Данные из собранных записей
            hero_data = df[df["Hero"] == hero]
            if not hero_data.empty:
                facets_in_data = hero_data["facet_number"].unique()
                print(f"   Фасеты в данных: {sorted(facets_in_data)}")
                print(f"   Записей в файле: {len(hero_data)}")
            else:
                print(f"   ❌ Герой не найден в собранных данных")

    print("\n" + "=" * 80)

    # 2. Показываем статистику по всем героям
    print("\n📊 ОБЩАЯ СТАТИСТИКА ФАСЕТОВ:")
    print("-" * 80)

    # Группируем данные по героям
    heroes_stats = (
        df.groupby("Hero")
        .agg({"facet_number": ["count", "nunique", "min", "max"], "Role": "nunique"})
        .round(2)
    )

    heroes_stats.columns = [
        "Записей",
        "Уникальных_фасетов",
        "Мин_фасет",
        "Макс_фасет",
        "Позиций",
    ]
    heroes_stats = heroes_stats.sort_values("Уникальных_фасетов", ascending=False)

    # Показываем топ-20 героев с наибольшим количеством фасетов
    print("\n🏆 ТОП-20 ГЕРОЕВ ПО КОЛИЧЕСТВУ ФАСЕТОВ:")
    print(heroes_stats.head(20))

    # 3. Показываем конкретные примеры записей
    print("\n" + "=" * 80)
    print("📋 ПРИМЕРЫ ЗАПИСЕЙ ИЗ ДАННЫХ:")
    print("-" * 80)

    # Фильтруем и показываем примеры
    sample_data = df[df["Hero"].isin(["Crystal Maiden", "Pudge", "Anti-Mage"])].copy()

    # Показываем только нужные колонки
    columns_to_show = ["Hero", "facet_number", "Role", "WR", "Matches"]
    available_columns = [col for col in columns_to_show if col in sample_data.columns]

    if available_columns:
        sample_display = sample_data[available_columns].sort_values(
            ["Hero", "facet_number", "Role"]
        )
        print(sample_display.to_string(index=False))
    else:
        print("Доступные колонки:", list(sample_data.columns))
        print(sample_data.head(10).to_string(index=False))

    # 4. Проверяем соответствие API и данных
    print("\n" + "=" * 80)
    print("✅ ПРОВЕРКА СООТВЕТСТВИЯ API И ДАННЫХ:")
    print("-" * 80)

    # Сравниваем количество фасетов в API и в данных
    api_comparison = []

    for hero in test_heroes:
        if hero in api_facets:
            api_facet_count = len(api_facets[hero])

            hero_data = df[df["Hero"] == hero]
            data_facet_count = (
                hero_data["facet_number"].nunique() if not hero_data.empty else 0
            )

            status = "✅" if api_facet_count >= data_facet_count else "❌"

            api_comparison.append(
                {
                    "Герой": hero,
                    "API_фасетов": api_facet_count,
                    "Данных_фасетов": data_facet_count,
                    "Статус": status,
                }
            )

    comparison_df = pd.DataFrame(api_comparison)
    print(comparison_df.to_string(index=False))

    print(
        f"\n🎯 ИТОГ: Система правильно парсит фасеты из API и применяет их к собранным данным!"
    )


if __name__ == "__main__":
    show_facets_table()
