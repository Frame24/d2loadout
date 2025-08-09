"""
Экспорт таблицы фасетов в CSV для проверки
"""

import pandas as pd
from modules.utils.facet_api_parser import FacetAPIParser


def export_facets_csv(output_path: str = "facets_table.csv") -> None:
    # Загружаем собранные данные
    df = pd.read_csv("heroes_data.csv")

    # Получаем маппинг фасетов из API
    parser = FacetAPIParser()
    api_facets = parser.get_hero_facets_mapping()  # {hero: {facet_name: order}}

    # Инвертируем в {hero: {order: facet_name}}
    inverted = {}
    for hero, name_to_order in api_facets.items():
        inverted[hero] = {order: name for name, order in name_to_order.items()}

    # Готовим агрегаты по (Hero, facet_number)
    have_wr = "WR" in df.columns
    have_matches = "Matches" in df.columns

    group_cols = ["Hero", "facet_number"]

    agg_map = {"Role": lambda s: ", ".join(sorted(set(s.dropna().astype(str))))}

    if have_matches:
        agg_map["Matches"] = "sum"
    if have_wr and have_matches:
        # Посчитаем взвешенный WR
        df["_wr_x_matches"] = df["WR"] * df["Matches"]
        agg_map["_wr_x_matches"] = "sum"

    grouped = df.groupby(group_cols).agg(agg_map).reset_index()

    # Переименуем и посчитаем итоговые поля
    grouped = grouped.rename(
        columns={
            "Role": "roles_present",
            "Matches": "matches_total",
        }
    )

    if have_wr and have_matches:
        # weighted WR = sum(WR*Matches)/sum(Matches)
        grouped["wr_weighted"] = (
            grouped["_wr_x_matches"] / grouped["matches_total"]
        ).round(2)
        grouped = grouped.drop(columns=["_wr_x_matches"])

    # Добавим facet_name из API (через инвертированный справочник)
    facet_names = []
    for _, row in grouped.iterrows():
        hero = row["Hero"]
        order = int(row["facet_number"]) if pd.notna(row["facet_number"]) else None
        name = None
        if hero in inverted and order in inverted[hero]:
            name = inverted[hero][order]
        facet_names.append(name)

    grouped["facet_name"] = facet_names

    # Отсортируем для удобства
    grouped = grouped[
        [
            "Hero",
            "facet_number",
            "facet_name",
            "roles_present",
        ]
        + (["matches_total"] if have_matches else [])
        + (["wr_weighted"] if have_wr and have_matches else [])
    ]

    grouped = grouped.sort_values(["Hero", "facet_number"]).reset_index(drop=True)

    # Сохраняем
    grouped.to_csv(output_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    export_facets_csv()
