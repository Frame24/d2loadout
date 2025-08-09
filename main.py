## Preparations
# !auto-py-to-exe
import sys

# Определяем, использовать ли print вместо display
if hasattr(sys, "frozen"):  # Если код выполняется в собранном файле

    def display(*args, **kwargs):
        print(*args, **kwargs)


import warnings

warnings.filterwarnings("ignore")
print("d2loadout update started")
import json
import os
import re
import pandas as pd
import numpy as np
import requests
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import ast
import html_to_json

chrome_options = webdriver.ChromeOptions()

chrome_options.add_argument("user-agent=" + UserAgent().random)
chrome_options.add_argument("--disable-blink-features")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--incognito")
chrome_options.add_argument("disable-infobars")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("detach", True)

chrome_options.add_argument("headless")
chrome_options.add_argument("window-size=1920x1080")
chrome_options.add_argument("disable-gpu")

chrome_options.page_load_strategy = "eager"


os.environ["PATH"] += r"C:\Program Files (x86)\Chromedriver.exe"
driver = webdriver.Chrome(options=chrome_options)
## Meta
link_meta = "https://dota2protracker.com/meta"
driver.implicitly_wait(3)
driver.get(link_meta)
driver.implicitly_wait(10)
from bs4 import BeautifulSoup
import pandas as pd
from selenium.webdriver.common.by import By
import time


def get_d2pt_page_table(driver):
    # Даем время на загрузку контента
    time.sleep(0.2)

    # Получаем HTML страницы
    page_source = driver.page_source

    # Парсим HTML с помощью BeautifulSoup
    soup = BeautifulSoup(page_source, "html.parser")

    # Ищем строки таблицы по их CSS-классу
    table_rows = soup.find_all("div", class_="grid", style=True)

    # Список для хранения данных
    data = []
    headers = []

    for index, row in enumerate(table_rows):
        # Проверяем, чтобы строка не была заголовком
        cols = row.find_all("div", recursive=False)

        if index == 0:
            # Считаем первую строку заголовком
            for col in cols:
                header_text = col.get_text(strip=True)
                headers.append(header_text if header_text else None)
            continue

        row_data = []
        for col in cols:
            # Проверяем наличие изображений для извлечения роли
            img = col.find("img", alt=True)
            if img:
                row_data.append(img["alt"])
                continue

            # Обрабатываем содержимое внутри span
            spans = col.find_all("span")
            if spans:
                span_text = " ".join([span.get_text(strip=True) for span in spans])
                row_data.append(span_text if span_text else None)
                continue

            # Извлекаем текст и убираем пустые значения
            text = col.get_text(strip=True)
            row_data.append(text if text else None)

        if row_data:  # Только если данные не пусты
            data.append(row_data)

    # Преобразуем список в DataFrame
    df_heroes_table = pd.DataFrame(data, columns=headers)

    # Убираем лишние строки или обрабатываем некорректные данные
    df_heroes_table = df_heroes_table.dropna(how="all")

    # Очистка данных в процентах и диапазонах
    def clean_data(value):
        if isinstance(value, str):
            if "%" in value:
                try:
                    return float(value.replace("%", ""))
                except ValueError:
                    return value  # Вернуть исходное значение, если не удалось преобразовать
            elif "(" in value and ")" in value:
                try:
                    main_value, range_values = value.split("(")
                    main_value = main_value.strip()
                    range_values = range_values.replace(")", "").split("-")
                    return {
                        "main": int(main_value),
                        "range_min": int(range_values[0]),
                        "range_max": int(range_values[1]),
                    }
                except ValueError:
                    return (
                        value  # Вернуть исходное значение, если формат не соответствует
                    )
        return value

    # Применяем очистку данных ко всем ячейкам
    df_heroes_table = df_heroes_table.map(clean_data)

    # Обработка типов данных для чисел
    df_heroes_table = df_heroes_table.apply(
        lambda x: x.convert_dtypes() if x.name != 2 else x
    )

    return df_heroes_table


# Пример использования:
# driver = ...  # Selenium WebDriver
# df = get_d2pt_page_table(driver)
# print(df)

print("checking meta...")
print("fetching heroes info for pos 1")
driver.find_element(By.XPATH, "//div[contains(text(), 'Carry')]").click()
df_1 = get_d2pt_page_table(driver)

print("fetching heroes info for pos 2")
driver.find_element(By.XPATH, "//div[contains(text(), 'Mid')]").click()
df_2 = get_d2pt_page_table(driver)

print("fetching heroes info for pos 3")
driver.find_element(By.XPATH, "//div[contains(text(), 'Off')]").click()
df_3 = get_d2pt_page_table(driver)

print("fetching heroes info for pos 4")
driver.find_element(By.XPATH, "//div[contains(text(), 'Pos 4')]").click()
df_4 = get_d2pt_page_table(driver)

print("fetching heroes info for pos 5")
driver.find_element(By.XPATH, "//div[contains(text(), 'Pos 5')]").click()
df_5 = get_d2pt_page_table(driver)

df_full = pd.concat([df_1, df_2, df_3, df_4, df_5], axis=0)
df_full
## Facets
link = "https://dota2protracker.com/facets"
driver.implicitly_wait(2)
driver.get(link)
hero_req = requests.get("https://dota2protracker.com/hero/Tiny")
import re

# Пример HTML-кода (замени на свой)
html_text = hero_req.text
# Регулярное выражение для извлечения объекта facetData
pattern = r"facetData:\s*({.*?})\s*\}\s*,"
constdata = re.findall(pattern, html_text, re.DOTALL)[0]

constdata

import js2py
import json
import pandas as pd

# Пример JavaScript-кода
js_code = f"""
var data = {constdata};

// Возвращаем JSON-строку facetData
JSON.stringify(data);
"""

# Исполняем JavaScript-код
result = js2py.eval_js(js_code)

if result:
    # Преобразуем JSON-строку в Python-словарь
    facet_data = json.loads(result)

    # Инициализируем пустой DataFrame
    all_facets_df = pd.DataFrame()

    # Итерация по всем ключам в facetData
    for key, value in facet_data.items():
        facets = value.get("facets", [])
        # Преобразуем каждый набор facets в DataFrame
        facets_data = []
        for facet in facets:
            if not facet.get("deprecated", False):  # Пропускаем deprecated
                facets_data.append(facet)

        facets_df = pd.DataFrame(facets_data)

        # Добавляем информацию о ключе, id и localized_name в DataFrame
        facets_df["key"] = key  # Ключ из facetData
        facets_df["id"] = value.get("id")
        facets_df["localized_name"] = value.get("localized_name")

        # Объединяем текущий DataFrame с общим
        all_facets_df = pd.concat([all_facets_df, facets_df], ignore_index=True)

    # Перенумерация facet_number
    all_facets_df["facet_number"] = all_facets_df.groupby(["key", "id"]).cumcount() + 1

    # Выводим общий DataFrame
    display(all_facets_df)
else:
    print("Данные не найдены или невалидны.")


def get_d2pt_page_table_facets(driver):
    time.sleep(0.2)
    # finding table rows in site and converting to format, readable by pandas
    category_name_elements = driver.find_elements(
        By.CSS_SELECTOR, ".flex.bg-d2pt-gray-3.gap-1"
    )
    category_name_elements += driver.find_elements(
        By.CSS_SELECTOR, ".flex.bg-d2pt-gray-4.gap-1"
    )
    hero_rows = [item.text.split("\n") for item in category_name_elements]
    hero_columns = [
        item
        for item in driver.find_element(
            By.CSS_SELECTOR, ".flex.gap-1.font-medium.text-sm.mb-1"
        ).text.split("\n")
        if item != "Trend"
    ]

    # Dataframe dtype converts
    df_heroes_table = pd.DataFrame(data=hero_rows, columns=hero_columns)
    df_heroes_table = df_heroes_table.convert_dtypes()
    df_heroes_table = df_heroes_table.round(1)
    return df_heroes_table


print("checking facets...")
print("fetching facets info for pos 1")
driver.find_element(By.XPATH, "//div[contains(text(), 'Carry')]").click()
df_1 = get_d2pt_page_table_facets(driver)
df_1["Role"] = "pos 1"

print("fetching facets info for pos 2")
driver.find_element(By.XPATH, "//div[contains(text(), 'Mid')]").click()
df_2 = get_d2pt_page_table_facets(driver)
df_2["Role"] = "pos 2"

print("fetching facets info for pos 3")
driver.find_element(By.XPATH, "//div[contains(text(), 'Off')]").click()
df_3 = get_d2pt_page_table_facets(driver)
df_3["Role"] = "pos 3"

print("fetching facets info for pos 4")
driver.find_element(By.XPATH, "//div[contains(text(), 'Pos 4')]").click()
df_4 = get_d2pt_page_table_facets(driver)
df_4["Role"] = "pos 4"

print("fetching facets info for pos 5")
driver.find_element(By.XPATH, "//div[contains(text(), 'Pos 5')]").click()
df_5 = get_d2pt_page_table_facets(driver)
df_5["Role"] = "pos 5"

df_full_facets = pd.concat([df_1, df_2, df_3, df_4, df_5], axis=0)

df_full_facets = df_full_facets.rename(
    {"Hero": "hero", "Facet": "facet", "Matches": "Matches", "Win Rate": "Win Rate"},
    axis=1,
)[["hero", "facet", "Matches", "Win Rate", "Role"]]

df_full_facets["Win Rate"] = df_full_facets["Win Rate"].apply(
    lambda x: x.replace("%", "")
)
df_full_facets = df_full_facets.convert_dtypes()

df_full_facets
## Results
print("creating in-game loadouts")
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


# Оставляем только уникальные значения в правом DataFrame
all_facets_df_unique = all_facets_df.drop_duplicates(
    subset=["localized_name"], keep="first"
)

# Выполняем объединение
df_final = pd.merge(
    df_full,
    all_facets_df_unique[["id", "localized_name"]],  # Оставляем только нужные столбцы
    left_on=["Hero"],  # Соответствие по названию фасета и герою
    right_on=["localized_name"],  # Название фасета и героя
    how="left",  # Оставляем все строки из df_full
)

# Переименовываем столбец "id" в "hero_id"
df_final.rename(columns={"id": "hero_id"}, inplace=True)

# Перемещаем "hero_id" на нулевую позицию
cols = ["hero_id"] + [col for col in df_final.columns if col != "hero_id"]
df_final = df_final[cols]

# Заменить hero_id на 76 для строк, где Hero = "Outworld Destroyer"
df_final.loc[df_final["Hero"] == "Outworld Destroyer", "hero_id"] = 76

# Разделяем столбец Expert
df_final["Expert Win Rate"] = (
    df_final["Expert"].str.extract(r"(\d+\.\d+)%").astype(float)
)
df_final["Expert Matches"] = df_final["Expert"].str.extract(r"\((\d+)\)").astype(int)

# Разделяем столбец WR 9500+ MMR
df_final["9500 Win Rate"] = (
    df_final["WR 9500+ MMR"].str.extract(r"(\d+\.\d+)%").astype(float)
)
df_final["9500 Matches"] = df_final["WR 9500+ MMR"].str.extract(r" (\d+) ").astype(int)

# Удаляем старые столбцы (если нужно)
df_final.drop(columns=["Expert", "WR 9500+ MMR"], inplace=True)

# Результат
display(df_final)

# Приводим названия фасетов к единому регистру
df_full_facets["facet_upper"] = df_full_facets["facet"].str.upper()  # В верхний регистр
all_facets_df["name_upper"] = all_facets_df["name"].str.upper()  # В верхний регистр

# Выполняем объединение (merge) двух DataFrame по колонкам с названиями фасетов
df_final_facets = pd.merge(
    df_full_facets,
    all_facets_df[
        ["facet_number", "id", "name_upper", "localized_name"]
    ],  # Оставляем только нужные столбцы
    left_on=["facet_upper", "hero"],  # Соответствие по названию фасета и герою
    right_on=["name_upper", "localized_name"],  # Название фасета и героя
    how="left",  # Оставляем все строки из df_full_facets
)

# Удаляем временные колонки с верхним регистром (если они не нужны)
df_final_facets.drop(columns=["facet_upper", "name_upper"], inplace=True)

# Переименовываем столбец "id" в "hero_id"
df_final_facets.rename(columns={"id": "hero_id"}, inplace=True)

# Перемещаем "hero_id" на нулевую позицию
cols = ["hero_id"] + [col for col in df_final_facets.columns if col != "hero_id"]
df_final_facets = df_final_facets[cols]

# Итоговые столбцы
df_final_facets = df_final_facets[
    ["hero_id", "hero", "facet", "Matches", "Win Rate", "Role", "facet_number"]
]

# Результат
display(df_final_facets)

config = {
    "version": 3,
    "configs": [
        # Фасеты
        HeroConfigProcessor(
            df_final_facets, "Facet Matches>200", data_type="facet"
        ).build_config(matches_threshold=200, wr_threshold=51),
        HeroConfigProcessor(
            df_final_facets, "Facet Matches>50", data_type="facet"
        ).build_config(matches_threshold=50, wr_threshold=51),
        # Регулярные конфиги
        HeroConfigProcessor(df_final, "Win Rate", data_type="regular").build_config(
            matches_threshold=200, wr_threshold=51
        ),
        HeroConfigProcessor(df_final, "D2PT", data_type="regular").build_config(
            matches_threshold=200, wr_threshold=0, sort_by="D2PT Rating"
        ),
        # Эксперты
        HeroConfigProcessor(
            df_final, "Expert Win Rate", data_type="regular"
        ).build_config(
            expert_matches_threshold=50,
            expert_wr_threshold=51,
            sort_by="Expert Win Rate",
        ),
        # 9500 MMR
        HeroConfigProcessor(
            df_final, "9500 Win Rate", data_type="regular"
        ).build_config(
            mmr_9500_matches_threshold=100,
            mmr_9500_wr_threshold=51,
            sort_by="9500 Win Rate",
        ),
    ],
}

import threading


threading.Thread(
    target=lambda: driver.quit() if driver.service.process else None
).start()
## Find Steam
import os
import winreg
import win32api


def read_reg(ep, p=r"", k=""):
    try:
        key = winreg.OpenKeyEx(ep, p)
        value = winreg.QueryValueEx(key, k)
        if key:
            winreg.CloseKey(key)
        return value[0]
    except Exception as e:
        return None
    return None


Path1 = "{}\\Microsoft\\Windows\\Start Menu\\Programs\\Steam\\Steam.lnk".format(
    os.getenv("APPDATA")
)
if os.path.exists(Path1):
    import sys
    import win32com.client

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(Path1)
    Path1Res = shortcut.Targetpath
else:
    Path1Res = False
Path2 = (
    str(
        read_reg(
            ep=winreg.HKEY_LOCAL_MACHINE,
            p=r"SOFTWARE\Wow6432Node\Valve\Steam",
            k="InstallPath",
        )
    )
    + r"\steam.exe"
)
Path3 = (
    str(
        read_reg(
            ep=winreg.HKEY_LOCAL_MACHINE, p=r"SOFTWARE\Valve\Steam", k="InstallPath"
        )
    )
    + r"\steam.exe"
)
if not os.path.exists(Path2):
    Path2 = None
if not os.path.exists(Path3):
    Path3 = None
PossiblePaths = [
    r"X:\Steam\steam.exe",
    r"X:\Program Files\Steam\steam.exe",
    r"X:\Program Files (x86)\Steam\steam.exe",
]
ValidHardPaths = []
for Drive in win32api.GetLogicalDriveStrings().split("\000")[:-1]:
    Drive = Drive.replace(":\\", "")
    for path in PossiblePaths:
        path = path.replace("X", Drive)
        if os.path.exists(path):
            ValidHardPaths.append(path)
if len(ValidHardPaths) == 0:
    ValidHardPaths = ["None"]
ValidHardPaths
steam_dir = os.path.dirname(os.path.realpath(ValidHardPaths[0]))
steam_dir = os.path.join(steam_dir, "userdata")
steam_dir
dirs_to_check = [
    os.path.join(steam_dir, id, "570", "remote", "cfg") for id in os.listdir(steam_dir)
]
cfg_dirs = [dir for dir in dirs_to_check if os.path.isdir(dir)]
cfg_dirs
from datetime import datetime

for dir in cfg_dirs:
    # Убедимся, что папка old_grid существует
    old_grid_dir = os.path.join(dir, "old_grid")
    os.makedirs(old_grid_dir, exist_ok=True)

    # Путь к текущему файлу конфигурации
    current_config_path = os.path.join(dir, "hero_grid_config.json")

    # Если текущий конфиг существует, переместим его в old_grid с отметкой времени
    if os.path.exists(current_config_path):
        timestamp = datetime.now().strftime("%Y%m%d")
        old_config_path = os.path.join(
            old_grid_dir, f"hero_grid_config_{timestamp}.json"
        )

        # Если файл с таким именем уже существует, удаляем его перед перемещением
        if os.path.exists(old_config_path):
            os.remove(old_config_path)

        os.rename(current_config_path, old_config_path)

    # Сохраняем новую версию конфигурации
    with open(current_config_path, "w") as f:
        json.dump(dict(config), f)
## Autorun
import getpass
import os
import sys

USER_NAME = getpass.getuser()
from win32com.client import Dispatch

bat_path = rf"C:\Users\{USER_NAME}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\{os.path.basename(sys.executable)}.lnk"
target = sys.executable

shell = Dispatch("WScript.Shell")
shortcut = shell.CreateShortCut(bat_path)
shortcut.Targetpath = target
shortcut.save()
print("Done!")

for remaining in range(2, 0, -1):
    time.sleep(1)
