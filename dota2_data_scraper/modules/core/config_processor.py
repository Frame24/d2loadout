"""
Процессор для создания конфигураций героев
"""

import pandas as pd
import json
import logging
import re
import requests
from typing import Dict, List, Optional
import os

from .data_manager import DataManager
from ..utils.steam_manager import SteamManager
from ..utils.facet_api_parser import FacetAPIParser
from ..config.hero_config import HeroConfigProcessor
from ..config.layout_optimizer import LayoutOptimizer, ScreenDimensions

logger = logging.getLogger(__name__)

# Порог «значимого» объёма матчей на роли: перцентиль считаем только по героям с Matches строго выше этого значения.
_ROLE_PCTL_SHARE = 0.0025
_ROLE_PCTL_MIN_MATCHES = 100
# WR-пресет: порог матчей = max(100, q-й перцентиль выборки по роли).
_WR_MATCH_PCTL_Q = 0.15
_WR_MATCH_MIN_AFTER_PCTL = 100


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

            # heroes_no_facets.csv больше не используется: в hero_configs.json только 2 пресета
            # (WR и D2PT) из heroes_data.csv. Удалите старый CSV из configs/, если он ещё лежит.

            mapping = None
            if not self._heroes_without_game_facets(heroes_df):
                parser = FacetAPIParser()
                mapping = parser.get_hero_facets_mapping()
                self.logger.info(
                    f"Маппинг фасетов загружен для {len(mapping)} героев (legacy CSV)"
                )

            # Обработка данных героев
            processed_heroes = self._process_heroes_data(heroes_df, mapping)
            if processed_heroes.empty:
                self.logger.error("Ошибка при обработке данных героев")
                return False

            # Сохранение обработанных данных
            self.data_manager.save_dataframe(processed_heroes, "processed_heroes.csv")

            # Ровно два конфига: WR (плоско по позициям) и D2PT (плоско по позициям).
            config = self._create_configs(processed_heroes)

            # Применяем оптимизированное расположение к основным конфигурациям
            self._apply_optimized_layout_to_configs(config)

            # Сохранение стандартной конфигурации
            config_success = self._save_config(config)
            if not config_success:
                self.logger.error("Ошибка при сохранении стандартной конфигурации")
                return False

            self.logger.info(
                "✅ Применено оптимизированное расположение Classic Optimized"
            )

            # Копируем конфигурацию в Steam
            config_file_path = os.path.join("configs", "hero_configs.json")
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

    @staticmethod
    def _heroes_without_game_facets(heroes_df: pd.DataFrame) -> bool:
        """True если в данных нет игровых фасетов (только агрегат / No Facet)."""
        if heroes_df.empty or "Facet" not in heroes_df.columns:
            return True
        s = heroes_df["Facet"]
        for v in s.dropna():
            if isinstance(v, str) and v.strip() and v.strip().lower() != "no facet":
                return False
        return True

    def _process_heroes_data(self, heroes_df: pd.DataFrame, mapping: Optional[Dict[str, Dict[str, int]]] = None) -> pd.DataFrame:
        """
        Обработка данных героев

        Args:
            heroes_df: DataFrame с данными героев
            mapping: Предзагруженный маппинг фасетов (если None, загрузится автоматически)

        Returns:
            Обработанный DataFrame
        """
        try:
            self.logger.info("Обработка данных героев...")

            # hero_id: если в CSV/API уже есть (stats API отдаёт hero_id), берём его;
            # иначе или при битом значении — маппинг имён через /api/heroes/list.
            heroes_df["hero_id"] = self._hero_ids_with_api_preference(heroes_df)

            if self._heroes_without_game_facets(heroes_df):
                heroes_df = heroes_df.copy()
                heroes_df["facet_name"] = "No Facet"
                heroes_df["facet_number"] = 1
                if "Expert" in heroes_df.columns:
                    heroes_df["Expert_WR"] = (
                        heroes_df["Expert"].astype(str).str.extract(r"(\d+\.?\d*)")
                    )
                    heroes_df["Expert_WR"] = pd.to_numeric(
                        heroes_df["Expert_WR"], errors="coerce"
                    )
                cols = list(heroes_df.columns)
                new_cols = []
                for pref in ["hero_id", "Hero", "facet_name", "facet_number"]:
                    if pref in cols and pref not in new_cols:
                        new_cols.append(pref)
                new_cols += [c for c in cols if c not in new_cols]
                processed_df = heroes_df[new_cols].copy()
                self.logger.info(
                    f"Обработано {len(processed_df)} записей (без маппинга фасетов)"
                )
                return processed_df

            # Используем переданный маппинг или загружаем новый (с кешированием)
            if mapping is None:
                parser = FacetAPIParser()
                mapping = parser.get_hero_facets_mapping()  # {hero_name: {facet_name: order}}

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

    def _hero_ids_with_api_preference(self, heroes_df: pd.DataFrame) -> pd.Series:
        """
        Строит серию hero_id: числовой id из данных (D2PT stats) имеет приоритет над
        сопоставлением по имени (displayName из heroes/list может расходиться с hero_name).
        """
        name_mapped = self._map_hero_names_to_ids(heroes_df["Hero"])
        if "hero_id" not in heroes_df.columns:
            return name_mapped
        api_raw = pd.to_numeric(heroes_df["hero_id"], errors="coerce")
        out = name_mapped.copy()
        valid = api_raw.notna() & (api_raw > 0)
        if valid.any():
            out.loc[valid] = api_raw.loc[valid].astype(int)
            n = int(valid.sum())
            self.logger.info(
                "hero_id из данных (API/CSV) для %s строк, остальные — по имени из heroes/list",
                n,
            )
        return out

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

    def _apply_optimized_layout_to_configs(self, config: Dict) -> None:
        """
        Применяет оптимизированное расположение Classic Optimized к существующим конфигурациям

        Args:
            config: Конфигурация с категориями для обновления
        """
        try:
            from ..config.layout_optimizer import LayoutOptimizer

            # Получаем оптимизированное расположение
            optimizer = LayoutOptimizer()
            layouts = optimizer.calculate_optimal_layouts()
            classic_layout = layouts["classic_optimized"]

            # Применяем к каждой конфигурации
            for cfg in config.get("configs", []):
                self._update_config_layout(cfg, classic_layout)

            self.logger.info(
                "Применено оптимизированное расположение ко всем конфигурациям"
            )

        except Exception as e:
            self.logger.error(
                f"Ошибка при применении оптимизированного расположения: {e}"
            )

    def _update_config_layout(self, config: Dict, layout_template) -> None:
        """
        Обновляет расположение категорий в конфигурации согласно шаблону

        Args:
            config: Конфигурация для обновления
            layout_template: Шаблон расположения элементов
        """
        # Создаем маппинг шаблона по именам категорий
        layout_map = {cat.name: cat for cat in layout_template}

        # Обновляем существующие категории
        for category in config.get("categories", []):
            cat_name = category.get("category_name", "")

            if cat_name in layout_map:
                template = layout_map[cat_name]
                category["x_position"] = template.x
                category["y_position"] = template.y
                category["width"] = template.width
                category["height"] = template.height

    def _calculate_dynamic_match_thresholds(self, heroes_df: pd.DataFrame) -> tuple[int, int, int]:
        """
        Вычисление динамических порогов матчей на основе процентилей датасета.

        Базовый порог входа: max(100, 30-й процентиль). Обычный/расширенный — для имён конфигов.

        Returns:
            Кортеж (базовый_порог, обычный_порог, расширенный_порог)
        """
        if "Matches" not in heroes_df.columns:
            self.logger.warning("Колонка Matches не найдена, используем значения по умолчанию")
            return (100, 50, 100)

        matches = heroes_df["Matches"].dropna()
        if matches.empty:
            self.logger.warning("Нет данных о матчах, используем значения по умолчанию")
            return (100, 50, 100)

        base_threshold = max(100, int(matches.quantile(0.30)))
        basic_threshold = int(matches.quantile(0.60))
        extended_threshold = int(matches.quantile(0.75))
        if extended_threshold <= basic_threshold:
            extended_threshold = basic_threshold + 1

        self.logger.info(
            f"📊 Пороги матчей: базовый=max(100,p30)={base_threshold}, "
            f"обычный={basic_threshold}, расширенный={extended_threshold}"
        )
        return (base_threshold, basic_threshold, extended_threshold)

    @staticmethod
    def _role_matches_inclusion_cutoff(matches_sum: int) -> int:
        """Нижняя граница отсечки: max(100, 0.25% от суммы матчей на роли). Перцентиль — только у героев с Matches > этого числа."""
        return max(
            _ROLE_PCTL_MIN_MATCHES,
            int(matches_sum * _ROLE_PCTL_SHARE),
        )

    @staticmethod
    def _wr_match_percentile_threshold_for_role(
        role_df: pd.DataFrame, q: float
    ) -> tuple[int, Dict[str, object]]:
        """
        Порог матчей для WR: q-й перцентиль Matches среди героев роли с
        Matches > max(100, 0.0025 * сумма_матчей_на_роли).
        Если таких нет — перцентиль по всем героям роли (fallback).
        """
        meta: Dict[str, object] = {
            "matches_sum": 0,
            "inclusion_cutoff": None,
            "heroes_in_percentile_sample": 0,
            "percentile_fallback_all_role": False,
        }
        m = role_df["Matches"].dropna()
        if m.empty:
            return _WR_MATCH_MIN_AFTER_PCTL, meta
        matches_sum = int(m.sum())
        meta["matches_sum"] = matches_sum
        cutoff = ConfigProcessor._role_matches_inclusion_cutoff(matches_sum)
        meta["inclusion_cutoff"] = cutoff
        eligible = m[m > cutoff]
        if eligible.empty:
            sample = m
            meta["percentile_fallback_all_role"] = True
        else:
            sample = eligible
        meta["heroes_in_percentile_sample"] = int(len(sample))
        thr = max(_WR_MATCH_MIN_AFTER_PCTL, int(sample.quantile(q)))
        return thr, meta

    @staticmethod
    def summarize_role_matches_and_percentiles(
        heroes_df: pd.DataFrame, q: float = _WR_MATCH_PCTL_Q,
    ) -> List[Dict[str, object]]:
        """
        По каждой роли: сумма матчей, отсечка для выборки перцентиля и итоговый порог q.
        """
        rows: List[Dict[str, object]] = []
        for role in ["pos 1", "pos 2", "pos 3", "pos 4", "pos 5"]:
            rd = heroes_df[heroes_df["Role"] == role]
            m = rd["Matches"].dropna()
            if m.empty:
                rows.append(
                    {
                        "role": role,
                        "heroes": 0,
                        "matches_sum": 0,
                        "inclusion_cutoff": None,
                        "heroes_in_percentile_sample": 0,
                        "percentile_fallback_all_role": False,
                        "pctl_q": q,
                        "pctl_value": None,
                    }
                )
                continue
            thr, meta = ConfigProcessor._wr_match_percentile_threshold_for_role(rd, q)
            rows.append(
                {
                    "role": role,
                    "heroes": int(len(m)),
                    "matches_sum": meta["matches_sum"],
                    "inclusion_cutoff": meta["inclusion_cutoff"],
                    "heroes_in_percentile_sample": meta["heroes_in_percentile_sample"],
                    "percentile_fallback_all_role": meta["percentile_fallback_all_role"],
                    "pctl_q": q,
                    "pctl_value": thr,
                }
            )
        return rows

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

            base_threshold, basic_threshold, extended_threshold = self._calculate_dynamic_match_thresholds(heroes_df)
            role_stats = self.summarize_role_matches_and_percentiles(
                heroes_df, q=_WR_MATCH_PCTL_Q
            )
            for s in role_stats:
                q_pct = int(round(float(s["pctl_q"]) * 100))
                fb = (
                    " (перцентиль по всем героям роли)"
                    if s.get("percentile_fallback_all_role")
                    else ""
                )
                self.logger.info(
                    "Роль %s: героев=%s, сумма_матчей=%s, отсечка перцентиля Matches>%s, "
                    "в выборке %s героев, %s-й перцентиль -> порог >= %s%s",
                    s["role"],
                    s["heroes"],
                    s["matches_sum"],
                    s["inclusion_cutoff"],
                    s["heroes_in_percentile_sample"],
                    q_pct,
                    s["pctl_value"],
                    fb,
                )

            config = {
                "version": 3,
                "configs": [
                    self._create_flat_position_config(
                        heroes_df,
                        "Win rate (max(100, p15) per role)",
                        "WR",
                        0,
                        category_label="WR",
                        wr_threshold=51,
                        max_heroes_per_position=None,
                        match_percentile_per_role=_WR_MATCH_PCTL_Q,
                    ),
                    self._create_flat_position_config(
                        heroes_df,
                        f"D2PT {base_threshold}+",
                        "D2PT Rating",
                        base_threshold,
                        category_label="D2PT",
                        rating_above_average=True,
                    ),
                    self._create_flat_position_config(
                        heroes_df,
                        "d2pt&wr",
                        "D2PT Rating",
                        base_threshold,
                        category_label="d2pt&wr",
                        rating_above_average=True,
                        final_sort_field="WR",
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

    def _create_flat_position_config(
        self,
        heroes_df: pd.DataFrame,
        config_name: str,
        sort_field: str,
        min_matches: int,
        *,
        category_label: str,
        wr_threshold: Optional[float] = None,
        rating_above_average: Optional[bool] = None,
        max_heroes_per_position: Optional[int] = 30,
        match_percentile_per_role: Optional[float] = None,
        final_sort_field: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Одна категория на позицию (pos 1..5), без сетки фасетов.
        max_heroes_per_position=None — без обрезки топ-N (все герои, прошедшие фильтры).
        match_percentile_per_role — если задан (сейчас 0.15 для WR), порог матчей считается
        отдельно по каждой роли по распределению Matches только для этой роли; min_matches не используется.
        final_sort_field — если задан, после отбора топ-N по sort_field порядок hero_ids задаётся этой колонкой
        (например WR при том же составе, что и D2PT).
        """
        try:
            if sort_field not in heroes_df.columns:
                self.logger.warning(
                    f"Колонка {sort_field!r} отсутствует, пропускаем '{config_name}'"
                )
                return None
            if "WR" not in heroes_df.columns:
                self.logger.warning("Колонка WR отсутствует")
                return None
            if "Role" not in heroes_df.columns:
                self.logger.warning("Колонка Role отсутствует")
                return None
            if final_sort_field is not None and final_sort_field not in heroes_df.columns:
                self.logger.warning(
                    f"Колонка {final_sort_field!r} отсутствует для final_sort, пропускаем '{config_name}'"
                )
                return None

            self.logger.info(f"Создание плоской конфигурации '{config_name}'...")

            if match_percentile_per_role is not None:
                if rating_above_average is not None:
                    self.logger.warning(
                        "match_percentile_per_role вместе с D2PT-фильтром не сочетается, используйте обычный min_matches"
                    )
                    return None
                q = match_percentile_per_role
                categories = []
                positions = ["pos 1", "pos 2", "pos 3", "pos 4", "pos 5"]
                for i, position in enumerate(positions):
                    role_df = heroes_df[heroes_df["Role"] == position]
                    if role_df.empty:
                        continue
                    mcol = role_df["Matches"].dropna()
                    if mcol.empty:
                        continue
                    thr, meta = self._wr_match_percentile_threshold_for_role(role_df, q)
                    if meta.get("percentile_fallback_all_role"):
                        self.logger.warning(
                            "Роль %s: нет героев с Matches > отсечки %s, перцентиль по всей роли",
                            position,
                            meta.get("inclusion_cutoff"),
                        )
                    pos_heroes = role_df[role_df["Matches"] >= thr].copy()
                    if wr_threshold is not None:
                        pos_heroes = pos_heroes[pos_heroes["WR"] >= wr_threshold]
                    if pos_heroes.empty:
                        continue
                    pos_heroes = pos_heroes.sort_values(sort_field, ascending=False)
                    hero_ids = pos_heroes["hero_id"].dropna().astype(int).tolist()
                    if not hero_ids:
                        continue
                    x = i * 240
                    y = 20
                    width = 220
                    height = 400
                    categories.append(
                        {
                            "category_name": f"POS {i + 1} Top {category_label}",
                            "x_position": x,
                            "y_position": y,
                            "width": width,
                            "height": height,
                            "hero_ids": hero_ids,
                        }
                    )
                if not categories:
                    self.logger.warning(
                        f"Не удалось создать категории для '{config_name}'"
                    )
                    return None
                return {"config_name": config_name, "categories": categories}

            ranked = heroes_df[heroes_df["Matches"] >= min_matches].copy()

            if ranked.empty:
                self.logger.warning(
                    f"Нет героев с >= {min_matches} матчами для '{config_name}'"
                )
                return None

            if wr_threshold is not None:
                ranked = ranked[ranked["WR"] >= wr_threshold]
                self.logger.info(f"Применён фильтр WR >= {wr_threshold}")

            if rating_above_average is not None:
                if "D2PT Rating" not in heroes_df.columns:
                    self.logger.warning("Колонка D2PT Rating отсутствует")
                    return None
                all_d2pt_values = heroes_df["D2PT Rating"]
                non_zero_d2pt = all_d2pt_values[
                    (all_d2pt_values > 0) & (all_d2pt_values.notna())
                ]
                if not non_zero_d2pt.empty:
                    avg_d2pt = non_zero_d2pt.mean()
                    ranked = (
                        ranked[ranked["D2PT Rating"] >= avg_d2pt]
                        if rating_above_average
                        else ranked[ranked["D2PT Rating"] < avg_d2pt]
                    )
                    self.logger.info(
                        f"Применён фильтр D2PT {'выше' if rating_above_average else 'ниже'} среднего ({avg_d2pt:.1f})"
                    )
                else:
                    self.logger.warning(
                        "Нет ненулевых значений D2PT Rating для вычисления среднего"
                    )

            if ranked.empty:
                self.logger.warning(
                    f"После фильтров не осталось данных для '{config_name}'"
                )
                return None

            categories = []
            positions = ["pos 1", "pos 2", "pos 3", "pos 4", "pos 5"]

            for i, position in enumerate(positions):
                pos_heroes = ranked[ranked["Role"] == position].copy()
                if (
                    max_heroes_per_position is not None
                    and len(pos_heroes) > max_heroes_per_position
                ):
                    pos_heroes = (
                        pos_heroes.sort_values(sort_field, ascending=False)
                        .head(max_heroes_per_position)
                        .copy()
                    )
                if not pos_heroes.empty:
                    order_col = (
                        final_sort_field
                        if final_sort_field is not None
                        else sort_field
                    )
                    pos_heroes = pos_heroes.sort_values(order_col, ascending=False)
                    hero_ids = pos_heroes["hero_id"].dropna().astype(int).tolist()
                    if hero_ids:
                        x = i * 240
                        y = 20
                        width = 220
                        height = 400
                        categories.append(
                            {
                                "category_name": f"POS {i + 1} Top {category_label}",
                                "x_position": x,
                                "y_position": y,
                                "width": width,
                                "height": height,
                                "hero_ids": hero_ids,
                            }
                        )

            if not categories:
                self.logger.warning(
                    f"Не удалось создать категории для '{config_name}'"
                )
                return None

            return {"config_name": config_name, "categories": categories}

        except Exception as e:
            self.logger.error(f"Ошибка при создании плоской конфигурации: {e}")
            return None

    def _create_no_facets_config(
        self, heroes_df: pd.DataFrame, min_matches: int = 100, max_heroes_per_position: int = 30
    ) -> Optional[Dict]:
        """
        Deprecated: дополнительная конфигурация из heroes_no_facets.csv (legacy Selenium).

        Порог матчей: min_matches (обычно max(100, 30-й процентиль)).
        Не более max_heroes_per_position героев на позицию.
        """
        try:
            self.logger.info(f"Создание конфигурации без фасетов (порог: {min_matches}+ матчей)...")

            filtered_df = heroes_df[heroes_df["Matches"] >= min_matches].copy()

            if filtered_df.empty:
                self.logger.warning(
                    f"Нет героев с {min_matches}+ матчами для конфигурации без фасетов"
                )
                return None

            if "D2PT Rating" in filtered_df.columns:
                filtered_df = filtered_df.sort_values("D2PT Rating", ascending=False)
            else:
                self.logger.warning(
                    "Колонка D2PT Rating не найдена, сортировка по умолчанию"
                )

            categories = []
            positions = ["pos 1", "pos 2", "pos 3", "pos 4", "pos 5"]

            for i, position in enumerate(positions):
                pos_heroes = filtered_df[filtered_df["Role"] == position]

                if not pos_heroes.empty:
                    top_heroes = pos_heroes.head(max_heroes_per_position)
                    hero_ids = top_heroes["hero_id"].dropna().astype(int).tolist()

                    if hero_ids:
                        # Простые расчеты позиций для конфигурации без фасетов
                        # Размещаем 5 позиций в ряд
                        x = i * 240  # Ширина + отступ
                        y = 20  # Отступ сверху
                        width = 220
                        height = 400

                        categories.append(
                            {
                                "category_name": f"POS {i + 1} Top D2PT",
                                "x_position": x,
                                "y_position": y,
                                "width": width,
                                "height": height,
                                "hero_ids": hero_ids,
                            }
                        )

            if not categories:
                self.logger.warning(
                    "Не удалось создать категории для конфигурации без фасетов"
                )
                return None

            return {"config_name": f"D2PT No Facets {min_matches}+", "categories": categories}

        except Exception as e:
            self.logger.error(f"Ошибка при создании конфигурации без фасетов: {e}")
            return None

    def _create_facet_config(
        self,
        heroes_df: pd.DataFrame,
        config_name: str,
        sort_field: str,
        min_matches: int,
        wr_threshold: Optional[int] = None,
        rating_above_average: Optional[bool] = None,
        max_heroes_per_position: int = 30,
    ) -> Dict:
        """
        Deprecated: сетка лодаутов POS x Facet (1 / 2 / 3+).

        Игровые фасеты в Dota 2 убраны; основной пайплайн использует
        _create_flat_position_config. Метод оставлен для совместимости.

        Фильтр по матчам: min_matches (обычно max(100, 30-й процентиль)).
        Для каждой позиции не более max_heroes_per_position записей: при превышении
        берутся топ по sort_field, что эквивалентно повышению порога матчей по позиции.
        """
        try:
            if "facet_number" not in heroes_df.columns:
                self.logger.warning(
                    "Поле facet_number отсутствует, пропускаем конфигурацию фасетов"
                )
                return None

            self.logger.info(f"Создание конфигурации '{config_name}'...")

            facets_data = heroes_df[heroes_df["Matches"] >= min_matches].copy()

            if facets_data.empty:
                self.logger.warning(f"Нет данных фасетов с >= {min_matches} матчей")
                return None

            if wr_threshold is not None:
                facets_data = facets_data[facets_data["WR"] >= wr_threshold]
                self.logger.info(f"Применено фильтр WR >= {wr_threshold}")

            if rating_above_average is not None:
                all_d2pt_values = heroes_df["D2PT Rating"]
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

            if facets_data.empty:
                self.logger.warning(
                    f"После применения всех фильтров не осталось данных для '{config_name}'"
                )
                return None

            categories = []

            for position in range(1, 6):
                pos_data = facets_data[facets_data["Role"] == f"pos {position}"].copy()

                if len(pos_data) > max_heroes_per_position:
                    pos_data = (
                        pos_data.sort_values(sort_field, ascending=False)
                        .head(max_heroes_per_position)
                        .copy()
                    )
                    self.logger.debug(
                        f"Позиция {position}: ограничено до {max_heroes_per_position} (было больше)"
                    )

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
            # Гарантируем наличие директории configs/
            os.makedirs("configs", exist_ok=True)
            target_path = os.path.join("configs", "hero_configs.json")
            with open(target_path, "w") as config_file:
                json.dump(config, config_file, indent=4, default=str)

            self.logger.info(f"Конфигурация сохранена в {target_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при сохранении конфигурации: {e}")
            return False
