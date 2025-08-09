"""
Экспорт чистого каталога фасетов из Dotabuff (без привязки к данным матчей)
"""

import pandas as pd
from modules.utils.facet_api_parser import FacetAPIParser


def export_facets_catalog(output_path: str = "facets_catalog.csv") -> None:
    parser = FacetAPIParser()
    mapping = parser.get_hero_facets_mapping()  # {hero_name: {facet_name: order}}

    rows = []
    for hero, name_to_order in mapping.items():
        # инвертируем для сортировки по order
        order_to_name = {order: name for name, order in name_to_order.items()}
        for order in sorted(order_to_name.keys()):
            rows.append(
                {
                    "Hero": hero,
                    "facet_number": order,
                    "facet_name": order_to_name[order],
                }
            )

    df = pd.DataFrame(rows).sort_values(["Hero", "facet_number"]).reset_index(drop=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    export_facets_catalog()
