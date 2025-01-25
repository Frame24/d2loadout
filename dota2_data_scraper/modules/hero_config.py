import pandas as pd


class HeroConfigProcessor:
    def __init__(self, df, name, data_type="facet"):
        """
        Класс для обработки и создания конфигураций на основе DataFrame.

        Args:
            df (pd.DataFrame): DataFrame с данными героев.
            name (str): Имя конфигурации.
            data_type (str): Тип данных ('facet' или 'regular').
        """
        self.df = df
        self.name = name
        self.data_type = data_type

    def get_hero_ids(
        self,
        position,
        facet_number=None,
        facet_id=None,
        wr_threshold=50,
        matches_threshold=50,
        expert_matches_threshold=None,
        expert_wr_threshold=None,
        mmr_9500_matches_threshold=None,
        mmr_9500_wr_threshold=None,
        rating_threshold=None,
        sort_by="Win Rate",
        ascending=False,
    ):
        """
        Получает список идентификаторов героев для указанной позиции.

        Args:
            position (int): Позиция героя (1 для pos 1, 2 для pos 2 и т.д.).
            facet_number (int, optional): Номер фасета.
            facet_id (int, optional): Идентификатор фасета (название фасета).
            wr_threshold (float, optional): Минимальный win rate.
            matches_threshold (int, optional): Минимальное количество матчей.
            expert_matches_threshold (int, optional): Минимальное количество экспертных матчей.
            expert_wr_threshold (float, optional): Минимальный экспертный win rate.
            mmr_9500_matches_threshold (int, optional): Минимальное количество матчей для 9500 MMR.
            mmr_9500_wr_threshold (float, optional): Минимальный win rate для 9500 MMR.
            rating_threshold (float, optional): Минимальный D2PT рейтинг.
            sort_by (str, optional): Поле для сортировки.
            ascending (bool, optional): Порядок сортировки.

        Returns:
            list: Список идентификаторов героев.
        """
        position_str = f"pos {position}"

        # Фильтруем данные по базовым критериям
        filtered_df = self.df[
            (self.df["Role"] == position_str)
            & (self.df["Matches"] > matches_threshold)
            & (self.df["Win Rate"] > wr_threshold)
        ]

        # Дополнительные фильтры
        if expert_matches_threshold is not None and "Expert Matches" in self.df.columns:
            filtered_df = filtered_df[
                filtered_df["Expert Matches"] > expert_matches_threshold
            ]
        if expert_wr_threshold is not None and "Expert Win Rate" in self.df.columns:
            filtered_df = filtered_df[
                filtered_df["Expert Win Rate"] > expert_wr_threshold
            ]
        if mmr_9500_matches_threshold is not None and "9500 Matches" in self.df.columns:
            filtered_df = filtered_df[
                filtered_df["9500 Matches"] > mmr_9500_matches_threshold
            ]
        if mmr_9500_wr_threshold is not None and "9500 Win Rate" in self.df.columns:
            filtered_df = filtered_df[
                filtered_df["9500 Win Rate"] > mmr_9500_wr_threshold
            ]
        if rating_threshold is not None and "D2PT Rating" in self.df.columns:
            filtered_df = filtered_df[filtered_df["D2PT Rating"] > rating_threshold]

        # Фильтрация для фасетов
        if self.data_type == "facet":
            if facet_number is not None:
                if facet_number == "3+":
                    filtered_df = filtered_df[filtered_df["facet_number"] > 2]
                else:
                    filtered_df = filtered_df[
                        filtered_df["facet_number"] == facet_number
                    ]
            if facet_id is not None:
                filtered_df = filtered_df[filtered_df["facet"] == facet_id]

        # Сортировка данных
        if sort_by in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)

        return filtered_df["hero_id"].tolist()

    def build_config(
        self,
        wr_threshold=50,
        matches_threshold=50,
        expert_matches_threshold=None,
        expert_wr_threshold=None,
        mmr_9500_matches_threshold=None,
        mmr_9500_wr_threshold=None,
        rating_threshold=None,
        sort_by="Win Rate",
        ascending=False,
    ):
        """
        Создает конфигурацию на основе обработанных данных.

        Args:
            wr_threshold (float, optional): Минимальный win rate.
            matches_threshold (int, optional): Минимальное количество матчей.
            expert_matches_threshold (int, optional): Минимальное количество экспертных матчей.
            expert_wr_threshold (float, optional): Минимальный экспертный win rate.
            mmr_9500_matches_threshold (int, optional): Минимальное количество матчей для 9500 MMR.
            mmr_9500_wr_threshold (float, optional): Минимальный win rate для 9500 MMR.
            rating_threshold (float, optional): Минимальный D2PT рейтинг.
            sort_by (str, optional): Поле для сортировки.
            ascending (bool, optional): Порядок сортировки.

        Returns:
            dict: Конфигурация категорий.
        """
        if self.data_type == "facet":
            return self._build_facet_config(
                wr_threshold,
                matches_threshold,
                expert_matches_threshold,
                expert_wr_threshold,
                mmr_9500_matches_threshold,
                mmr_9500_wr_threshold,
                rating_threshold,
                sort_by,
                ascending,
            )
        elif self.data_type == "regular":
            return self._build_regular_config(
                wr_threshold,
                matches_threshold,
                expert_matches_threshold,
                expert_wr_threshold,
                mmr_9500_matches_threshold,
                mmr_9500_wr_threshold,
                rating_threshold,
                sort_by,
                ascending,
            )
        else:
            raise ValueError(f"Unsupported data type: {self.data_type}")

    def _build_facet_config(
        self,
        wr_threshold,
        matches_threshold,
        expert_matches_threshold,
        expert_wr_threshold,
        mmr_9500_matches_threshold,
        mmr_9500_wr_threshold,
        rating_threshold,
        sort_by,
        ascending,
    ):
        margin = 20
        max_height = 570
        max_width = 1180 - 100
        width = max_width / 5 - margin
        height = max_height / 2 - margin

        height_3 = (max_height / 5) - 20
        width_3 = 70

        categories = []
        for position in range(1, 6):
            hero_ids_facet_1 = self.get_hero_ids(
                position,
                facet_number=1,
                wr_threshold=wr_threshold,
                matches_threshold=matches_threshold,
                expert_matches_threshold=expert_matches_threshold,
                expert_wr_threshold=expert_wr_threshold,
                mmr_9500_matches_threshold=mmr_9500_matches_threshold,
                mmr_9500_wr_threshold=mmr_9500_wr_threshold,
                rating_threshold=rating_threshold,
                sort_by=sort_by,
                ascending=ascending,
            )
            hero_ids_facet_2 = self.get_hero_ids(
                position,
                facet_number=2,
                wr_threshold=wr_threshold,
                matches_threshold=matches_threshold,
                expert_matches_threshold=expert_matches_threshold,
                expert_wr_threshold=expert_wr_threshold,
                mmr_9500_matches_threshold=mmr_9500_matches_threshold,
                mmr_9500_wr_threshold=mmr_9500_wr_threshold,
                rating_threshold=rating_threshold,
                sort_by=sort_by,
                ascending=ascending,
            )
            hero_ids_facet_3_plus = self.get_hero_ids(
                position,
                facet_number="3+",
                wr_threshold=wr_threshold,
                matches_threshold=matches_threshold,
                expert_matches_threshold=expert_matches_threshold,
                expert_wr_threshold=expert_wr_threshold,
                mmr_9500_matches_threshold=mmr_9500_matches_threshold,
                mmr_9500_wr_threshold=mmr_9500_wr_threshold,
                rating_threshold=rating_threshold,
                sort_by=sort_by,
                ascending=ascending,
            )

            if hero_ids_facet_1:
                categories.append(
                    {
                        "category_name": f"Pos {position} F 1",
                        "x_position": (width + margin) * (position - 1),
                        "y_position": 0,
                        "width": width,
                        "height": height,
                        "hero_ids": hero_ids_facet_1,
                    }
                )
            if hero_ids_facet_2:
                categories.append(
                    {
                        "category_name": f"Pos {position} F 2",
                        "x_position": (width + margin) * (position - 1),
                        "y_position": height + margin,
                        "width": width,
                        "height": height,
                        "hero_ids": hero_ids_facet_2,
                    }
                )
            if hero_ids_facet_3_plus:
                categories.append(
                    {
                        "category_name": f"Pos {position} F 3+",
                        "x_position": max_width + margin,
                        "y_position": (height_3 + margin) * (position - 1),
                        "width": width_3,
                        "height": height_3,
                        "hero_ids": hero_ids_facet_3_plus,
                    }
                )

        return {
            "config_name": self.name,
            "categories": categories,
        }

    def _build_regular_config(
        self,
        wr_threshold,
        matches_threshold,
        expert_matches_threshold,
        expert_wr_threshold,
        mmr_9500_matches_threshold,
        mmr_9500_wr_threshold,
        rating_threshold,
        sort_by,
        ascending,
    ):
        margin = 20
        width = 585 - margin
        height = 189 - margin

        included_hero_ids = set()
        categories = []

        for position in range(1, 6):
            hero_ids_regular = self.get_hero_ids(
                position,
                wr_threshold=wr_threshold,
                matches_threshold=matches_threshold,
                expert_matches_threshold=expert_matches_threshold,
                expert_wr_threshold=expert_wr_threshold,
                mmr_9500_matches_threshold=mmr_9500_matches_threshold,
                mmr_9500_wr_threshold=mmr_9500_wr_threshold,
                rating_threshold=rating_threshold,
                sort_by=sort_by,
                ascending=ascending,
            )

            included_hero_ids.update(hero_ids_regular)

            if position <= 3:
                categories.append(
                    {
                        "category_name": f"Regular Pos {position}",
                        "x_position": 0.0,
                        "y_position": (height + margin) * (position - 1),
                        "width": width,
                        "height": height,
                        "hero_ids": hero_ids_regular,
                    }
                )
            else:
                categories.append(
                    {
                        "category_name": f"Regular Pos {position}",
                        "x_position": width + margin,
                        "y_position": (height + margin) * (position - 4),
                        "width": width,
                        "height": height,
                        "hero_ids": hero_ids_regular,
                    }
                )

        all_hero_ids = set(self.df["hero_id"].unique())
        not_included_hero_ids = list(all_hero_ids - included_hero_ids)

        if not_included_hero_ids:
            categories.append(
                {
                    "category_name": "Not-Included",
                    "x_position": width + margin,
                    "y_position": (height + margin) * 2,
                    "width": width,
                    "height": height,
                    "hero_ids": not_included_hero_ids,
                }
            )

        return {
            "config_name": self.name,
            "categories": categories,
        }