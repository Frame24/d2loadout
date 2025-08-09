"""
Процессор для создания конфигураций героев
"""

import pandas as pd
import json
import logging
import re
import requests
from typing import Dict, List, Optional

from .data_manager import DataManager
from ..utils.steam_manager import SteamManager
from ..utils.facet_api_parser import FacetAPIParser

logger = logging.getLogger(__name__)


class ConfigProcessor:
    """Класс для обработки и создания конфигураций героев"""

    def __init__(self):
        self.logger = logger
        self.data_manager = DataManager()
        self.steam_manager = SteamManager()  # Добавляем Steam Manager

    def process_all_data(self) -> bool:
        """
        Обработка всех данных и создание конфигураций

        Returns:
            True если обработка успешна, False в противном случае
        """
        try:
            self.logger.info("Начало обработки всех данных...")

            # Загрузка данных
            heroes_df = self.data_manager.load_dataframe("heroes_data.csv")

            if heroes_df is None:
                self.logger.error("Не удалось загрузить данные героев")
                return False

            # Обработка данных героев
            processed_heroes = self._process_heroes_data(heroes_df)
            if processed_heroes.empty:
                self.logger.error("Ошибка при обработке данных героев")
                return False

            # Сохранение обработанных данных
            self.data_manager.save_dataframe(processed_heroes, "processed_heroes.csv")

            # Создание конфигураций
            config = self._create_configs(processed_heroes)

            # Сохранение конфигурации
            config_success = self._save_config(config)
            if not config_success:
                self.logger.error("Ошибка при сохранении конфигурации")
                return False

            # Копируем конфигурацию в Steam
            config_file_path = "hero_configs.json"
            steam_success = self.steam_manager.copy_config_to_steam(config_file_path)
            if steam_success:
                self.logger.info("✅ Конфигурация скопирована в Steam")
            else:
                self.logger.warning(
                    "⚠️ Не удалось скопировать в Steam (файл сохранен локально)"
                )

            self.logger.info("Обработка всех данных завершена успешно")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при обработке данных: {e}")
            return False

    def _process_heroes_data(self, heroes_df: pd.DataFrame) -> pd.DataFrame:
        """
        Обработка данных героев

        Args:
            heroes_df: DataFrame с данными героев

        Returns:
            Обработанный DataFrame
        """
        try:
            self.logger.info("Обработка данных героев...")

            # Добавление hero_id на основе имени героя
            heroes_df["hero_id"] = self._map_hero_names_to_ids(heroes_df["Hero"])

            # Загружаем маппинг фасетов один раз
            parser = FacetAPIParser()
            mapping = (
                parser.get_hero_facets_mapping()
            )  # {hero_name: {facet_name: order}}

            # Заполняем facet_name из исходных данных, если есть колонка 'Facet'
            if "Facet" in heroes_df.columns:
                heroes_df["facet_name"] = heroes_df["Facet"].where(
                    heroes_df["Facet"].notna(), None
                )
            else:
                heroes_df["facet_name"] = None

            # Вычисляем fallback-порядок появления фасетов для каждого (Hero, Role)
            try:
                heroes_df["_fallback_order"] = (
                    heroes_df.groupby(["Hero", "Role"]).cumcount() + 1
                )
            except Exception:
                heroes_df["_fallback_order"] = 1

            # Определяем facet_number строго по facet_name; фолбек — fallback_order
            resolved_numbers: List[Optional[int]] = []
            resolved_names: List[Optional[str]] = []
            for _, row in heroes_df.iterrows():
                hero = row.get("Hero")
                name = row.get("facet_name")
                fallback_order = row.get("_fallback_order")

                # Если имени нет, попробуем восстановить по fallback_order через инверсию маппинга
                if not isinstance(name, str) and isinstance(hero, str):
                    name_to_order = mapping.get(hero, {})
                    order_to_name = {v: k for k, v in name_to_order.items()}
                    if isinstance(fallback_order, (int, float)):
                        candidate = order_to_name.get(int(fallback_order))
                        if isinstance(candidate, str):
                            name = candidate

                # Находим номер по имени в маппинге
                num = None
                if isinstance(hero, str) and isinstance(name, str):
                    name_to_order = mapping.get(hero, {})
                    num = name_to_order.get(name)

                # Фолбек на порядковый номер внутри героя и роли
                if num is None:
                    num = int(fallback_order) if pd.notna(fallback_order) else 1
                resolved_numbers.append(int(num))
                resolved_names.append(
                    name if isinstance(name, str) else f"Facet {int(num)}"
                )

            heroes_df["facet_name"] = resolved_names
            heroes_df["facet_number"] = resolved_numbers

            # Убираем служебную колонку
            if "_fallback_order" in heroes_df.columns:
                heroes_df = heroes_df.drop(columns=["_fallback_order"])

            # Разбиваем Expert на отдельные поля если нужно
            if "Expert" in heroes_df.columns:
                heroes_df["Expert_WR"] = (
                    heroes_df["Expert"].astype(str).str.extract(r"(\d+\.?\d*)")
                )
                heroes_df["Expert_WR"] = pd.to_numeric(
                    heroes_df["Expert_WR"], errors="coerce"
                )

            # Перемещаем hero_id в начало и facet_name перед facet_number
            cols = list(heroes_df.columns)
            new_cols = []
            for pref in ["hero_id", "Hero", "facet_name", "facet_number"]:
                if pref in cols and pref not in new_cols:
                    new_cols.append(pref)
            new_cols += [c for c in cols if c not in new_cols]

            processed_df = heroes_df[new_cols].copy()

            self.logger.info(f"Обработано {len(processed_df)} записей героев")
            return processed_df

        except Exception as e:
            self.logger.error(f"Ошибка при обработке данных героев: {e}")
            return pd.DataFrame()

    def _load_heroes_from_api(self) -> Dict[str, int]:
        """
        Загрузка маппинга героев из API dota2protracker.com

        Returns:
            Словарь {hero_name: hero_id}
        """
        try:
            self.logger.info("Загрузка данных героев из API...")

            response = requests.get(
                "https://dota2protracker.com/api/heroes/list", timeout=10
            )
            response.raise_for_status()

            api_data = response.json()
            hero_mapping = {hero["displayName"]: hero["hero_id"] for hero in api_data}

            self.logger.info(f"✅ Загружено {len(hero_mapping)} героев из API")
            return hero_mapping

        except requests.RequestException as e:
            self.logger.warning(f"⚠️ Не удалось загрузить данные из API: {e}")
            return self._get_fallback_mapping()
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка при обработке API данных: {e}")
            return self._get_fallback_mapping()

    def _get_fallback_mapping(self) -> Dict[str, int]:
        """
        Резервный маппинг героев на случай недоступности API

        Returns:
            Словарь с основными героями
        """
        self.logger.info("Использование резервного маппинга героев")
        return {
            "Anti-Mage": 1,
            "Axe": 2,
            "Bane": 3,
            "Bloodseeker": 4,
            "Crystal Maiden": 5,
            "Drow Ranger": 6,
            "Earthshaker": 7,
            "Juggernaut": 8,
            "Mirana": 9,
            "Morphling": 10,
            "Shadow Fiend": 11,
            "Phantom Lancer": 12,
            "Puck": 13,
            "Pudge": 14,
            "Razor": 15,
            "Sand King": 16,
            "Storm Spirit": 17,
            "Sven": 18,
            "Tiny": 19,
            "Vengeful Spirit": 20,
            "Windranger": 21,
            "Zeus": 22,
            "Kunkka": 23,
            "Lina": 25,
            "Lion": 26,
            "Shadow Shaman": 27,
            "Slardar": 28,
            "Tidehunter": 29,
            "Witch Doctor": 30,
            "Lich": 31,
            "Riki": 32,
            "Enigma": 33,
            "Tinker": 34,
            "Sniper": 35,
            "Necrophos": 36,
            "Warlock": 37,
            "Beastmaster": 38,
            "Queen of Pain": 39,
            "Venomancer": 40,
            "Faceless Void": 41,
            "Wraith King": 42,
            "Death Prophet": 43,
            "Phantom Assassin": 44,
            "Pugna": 45,
            "Templar Assassin": 46,
            "Viper": 47,
            "Luna": 48,
            "Dragon Knight": 49,
            "Dazzle": 50,
            "Clockwerk": 51,
            "Leshrac": 52,
            "Nature's Prophet": 53,
            "Lifestealer": 54,
            "Dark Seer": 55,
            "Clinkz": 56,
            "Omniknight": 57,
            "Enchantress": 58,
            "Huskar": 59,
            "Night Stalker": 60,
            "Broodmother": 61,
            "Bounty Hunter": 62,
            "Weaver": 63,
            "Jakiro": 64,
            "Batrider": 65,
            "Chen": 66,
            "Spectre": 67,
            "Ancient Apparition": 68,
            "Doom": 69,
            "Ursa": 70,
            "Spirit Breaker": 71,
            "Gyrocopter": 72,
            "Alchemist": 73,
            "Invoker": 74,
            "Silencer": 75,
            "Outworld Destroyer": 76,
            "Lycan": 77,
            "Brewmaster": 78,
            "Shadow Demon": 79,
            "Lone Druid": 80,
            "Chaos Knight": 81,
            "Meepo": 82,
            "Treant Protector": 83,
            "Ogre Magi": 84,
            "Undying": 85,
            "Rubick": 86,
            "Disruptor": 87,
            "Nyx Assassin": 88,
            "Naga Siren": 89,
            "Keeper of the Light": 90,
            "Io": 91,
            "Visage": 92,
            "Slark": 93,
            "Medusa": 94,
            "Troll Warlord": 95,
            "Centaur Warrunner": 96,
            "Magnus": 97,
            "Timbersaw": 98,
            "Bristleback": 99,
            "Tusk": 100,
            "Skywrath Mage": 101,
            "Abaddon": 102,
            "Elder Titan": 103,
            "Legion Commander": 104,
            "Techies": 105,
            "Ember Spirit": 106,
            "Earth Spirit": 107,
            "Underlord": 108,
            "Terrorblade": 109,
            "Phoenix": 110,
            "Oracle": 111,
            "Winter Wyvern": 112,
            "Arc Warden": 113,
            "Monkey King": 114,
            "Dark Willow": 119,
            "Pangolier": 120,
            "Grimstroke": 121,
            "Hoodwink": 123,
            "Void Spirit": 126,
            "Snapfire": 128,
            "Mars": 129,
            "Ringmaster": 131,
            "Dawnbreaker": 135,
            "Marci": 136,
            "Primal Beast": 137,
            "Muerta": 138,
            "Kez": 145,
        }

    def _map_hero_names_to_ids(self, hero_names: pd.Series) -> pd.Series:
        """
        Маппинг имен героев к их ID с использованием API

        Args:
            hero_names: Серия с именами героев

        Returns:
            Серия с hero_id
        """
        hero_mapping = self._load_heroes_from_api()
        mapped_ids = hero_names.map(hero_mapping)

        # Проверяем количество нераспознанных героев
        unmapped_count = mapped_ids.isna().sum()
        if unmapped_count > 0:
            unmapped_heroes = hero_names[mapped_ids.isna()].unique()
            self.logger.warning(
                f"❌ Не найдены ID для {unmapped_count} героев: {list(unmapped_heroes)}"
            )

        return mapped_ids.fillna(0)

    def _create_configs(self, heroes_df: pd.DataFrame) -> Dict:
        """
        Создание конфигураций

        Args:
            heroes_df: DataFrame с данными героев

        Returns:
            Словарь с конфигурациями
        """
        try:
            self.logger.info("Создание конфигураций...")

            config = {
                "version": 3,
                "configs": [
                    # Конфигурации фасетов
                    self._create_facet_config(
                        heroes_df, "Win rate", "WR", 100, wr_threshold=51
                    ),
                    self._create_facet_config(
                        heroes_df, "D2PT", "D2PT Rating", 100, rating_above_average=True
                    ),
                ],
            }

            # Убираем None значения из списка конфигураций
            config["configs"] = [c for c in config["configs"] if c is not None]

            self.logger.info(f"Создано {len(config['configs'])} конфигураций")
            return config

        except Exception as e:
            self.logger.error(f"Ошибка при создании конфигураций: {e}")
            return {}

    def _create_facet_config(
        self,
        heroes_df: pd.DataFrame,
        config_name: str,
        sort_field: str,
        min_matches: int,
        wr_threshold: Optional[int] = None,
        rating_above_average: Optional[bool] = None,
    ) -> Dict:
        """
        Создание конфигурации по фасетам

        Args:
            heroes_df: DataFrame с данными героев
            config_name: Название конфигурации
            sort_field: Поле для сортировки
            min_matches: Минимальное количество матчей
            wr_threshold: Порог WR для фильтрации (для Win rate)
            rating_above_average: Флаг для фильтрации D2PT (True для выше среднего)

        Returns:
            Конфигурация по фасетам или None
        """
        try:
            if "facet_number" not in heroes_df.columns:
                self.logger.warning(
                    "Поле facet_number отсутствует, пропускаем конфигурацию фасетов"
                )
                return None

            self.logger.info(f"Создание конфигурации '{config_name}'...")

            # Фильтруем данные с достаточным количеством матчей
            facets_data = heroes_df[heroes_df["Matches"] >= min_matches].copy()

            if facets_data.empty:
                self.logger.warning(f"Нет данных фасетов с >= {min_matches} матчей")
                return None

            # Применяем дополнительные фильтры, если они указаны
            if wr_threshold is not None:
                facets_data = facets_data[facets_data["WR"] >= wr_threshold]
                self.logger.info(f"Применено фильтр WR >= {wr_threshold}")

            if rating_above_average is not None:
                # Вычисляем средний D2PT для всех героев (не только отфильтрованных)
                all_d2pt_values = heroes_df["D2PT Rating"]
                # Исключаем нулевые и NaN значения
                non_zero_d2pt = all_d2pt_values[
                    (all_d2pt_values > 0) & (all_d2pt_values.notna())
                ]
                if not non_zero_d2pt.empty:
                    avg_d2pt = non_zero_d2pt.mean()
                    facets_data = (
                        facets_data[facets_data["D2PT Rating"] >= avg_d2pt]
                        if rating_above_average
                        else facets_data[facets_data["D2PT Rating"] < avg_d2pt]
                    )
                    self.logger.info(
                        f"Применен фильтр D2PT {'выше' if rating_above_average else 'ниже'} среднего ({avg_d2pt:.1f})"
                    )
                else:
                    self.logger.warning(
                        "Нет ненулевых значений D2PT Rating для вычисления среднего"
                    )

            # Проверяем, остались ли данные после применения всех фильтров
            if facets_data.empty:
                self.logger.warning(
                    f"После применения всех фильтров не осталось данных для '{config_name}'"
                )
                return None

            # Создаем конфигурацию фасетов
            categories = []

            # Группируем по позициям и номерам фасетов
            for position in range(1, 6):
                pos_data = facets_data[facets_data["Role"] == f"pos {position}"]

                for facet_num in [1, 2, 3]:
                    if facet_num <= 2:
                        facet_data = pos_data[pos_data["facet_number"] == facet_num]
                    else:
                        # Для фасета 3+ берем все фасеты с номером >= 3
                        facet_data = pos_data[pos_data["facet_number"] >= 3]

                    if not facet_data.empty:
                        # Сортируем по указанному полю (по убыванию)
                        facet_data = facet_data.sort_values(sort_field, ascending=False)
                        hero_ids = facet_data["hero_id"].tolist()

                        # Рассчитываем позиции на экране
                        if facet_num <= 2:
                            # Фасеты 1 и 2 - основная сетка
                            x_pos = (position - 1) * 230
                            y_pos = (facet_num - 1) * 285
                            width = 210
                            height = 265
                            facet_name = f"POS {position} F {facet_num}"
                        else:
                            # Фасеты 3+ - боковая панель
                            x_pos = 1150
                            y_pos = (position - 1) * 110
                            width = 70
                            height = 90
                            facet_name = f"POS {position} F 3+"

                        categories.append(
                            {
                                "category_name": facet_name,
                                "x_position": x_pos,
                                "y_position": y_pos,
                                "width": width,
                                "height": height,
                                "hero_ids": hero_ids,
                            }
                        )

            if categories:
                return {
                    "config_name": config_name,
                    "categories": categories,
                }
            else:
                self.logger.warning(
                    f"Не удалось создать категории для конфигурации '{config_name}'"
                )
                return None

        except Exception as e:
            self.logger.error(f"Ошибка при создании конфигурации '{config_name}': {e}")
            return None

    def _save_config(self, config: Dict) -> bool:
        """
        Сохранение конфигурации в файл

        Args:
            config: Словарь с конфигурацией

        Returns:
            True если сохранение успешно, False в противном случае
        """
        try:
            with open("hero_configs.json", "w") as config_file:
                json.dump(config, config_file, indent=4, default=str)

            self.logger.info("Конфигурация сохранена в hero_configs.json")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при сохранении конфигурации: {e}")
            return False
