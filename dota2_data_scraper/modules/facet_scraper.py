import re
import requests
import js2py
import json
import pandas as pd
import time
import logging
from selenium.webdriver.common.by import By

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_facet_data(hero_url):
    """
    Получение данных о герое с веб-сайта Dota2ProTracker.
    """
    try:
        logging.info(f"Запрос данных с {hero_url}")
        hero_req = requests.get(hero_url, timeout=10)
        hero_req.raise_for_status()  # Проверка успешного ответа сервера
        html_text = hero_req.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса: {e}")
        return None

    # Регулярное выражение для извлечения объекта facetData
    pattern = r'facetData:\s*({.*?})\s*\}\s*,'
    match = re.findall(pattern, html_text, re.DOTALL)

    if not match:
        logging.warning("Данные facetData не найдены или невалидны.")
        return None

    constdata = match[0]

    # Исполнение JS-кода для преобразования данных
    try:
        js_code = f"""
        var data = {constdata};
        JSON.stringify(data);
        """
        result = js2py.eval_js(js_code)
        return json.loads(result)
    except Exception as e:
        logging.error(f"Ошибка при обработке JS: {e}")
        return None

def process_facet_data(facet_data):
    """
    Обработка полученных данных и преобразование их в DataFrame.
    """
    logging.info("Обработка данных facetData...")
    all_facets_df = pd.DataFrame()

    # Итерация по всем ключам в facetData
    for key, value in facet_data.items():
        facets = value.get("facets", [])

        # Преобразуем каждый набор facets в DataFrame
        facets_data = []
        for facet in facets:
            if not facet.get("deprecated", False):  # Пропускаем устаревшие данные
                facets_data.append(facet)

        facets_df = pd.DataFrame(facets_data)

        # Добавляем информацию о ключе, id и имени героя в DataFrame
        facets_df["key"] = key
        facets_df["id"] = value.get("id")
        facets_df["localized_name"] = value.get("localized_name")

        # Объединяем текущий DataFrame с общим
        all_facets_df = pd.concat([all_facets_df, facets_df], ignore_index=True)

    # Перенумерация facet_number
    all_facets_df["facet_number"] = (
        all_facets_df.groupby(["key", "id"]).cumcount() + 1
    )

    logging.info("Обработка завершена.")
    return all_facets_df

def get_d2pt_page_table_facets(driver):
    """
    Сбор данных таблицы Facets через Selenium и преобразование в pandas DataFrame.
    """
    logging.info("Извлечение данных таблицы Facets...")
    time.sleep(0.2)

    # Извлекаем строки таблицы с сайта
    category_name_elements = driver.find_elements(By.CSS_SELECTOR, ".flex.bg-d2pt-gray-3.gap-1")
    category_name_elements += driver.find_elements(By.CSS_SELECTOR, ".flex.bg-d2pt-gray-4.gap-1")

    hero_rows = [item.text.split("\n") for item in category_name_elements]
    hero_columns = [
        item for item in driver.find_element(By.CSS_SELECTOR, ".flex.gap-1.font-medium.text-sm.mb-1").text.split("\n")
        if item != "Trend"
    ]

    # Преобразование данных в DataFrame
    df_heroes_table = pd.DataFrame(data=hero_rows, columns=hero_columns)
    df_heroes_table = df_heroes_table.convert_dtypes()
    df_heroes_table = df_heroes_table.round(1)
    
    logging.info("Извлечение таблицы завершено.")
    return df_heroes_table

def click_position(driver, position_xpath):
    """
    Нажимает на вкладку с указанной позицией на сайте.
    """
    logging.info(f"Клик по вкладке: {position_xpath}")
    driver.find_element(By.XPATH, position_xpath).click()
    time.sleep(0.5)

def collect_position_data(driver, role, xpath):
    """
    Сбор данных по конкретной позиции (Carry, Mid и т.д.).
    """
    click_position(driver, xpath)
    df = get_d2pt_page_table_facets(driver)
    df["Role"] = role
    return df

def scrape_facet_data(driver):
    """
    Основная функция для сбора данных по всем позициям.
    """
    logging.info("Начало сбора данных по позициям Facets...")

    positions = {
        "pos 1": "//div[contains(text(), 'Carry')]",
        "pos 2": "//div[contains(text(), 'Mid')]",
        "pos 3": "//div[contains(text(), 'Off')]",
        "pos 4": "//div[contains(text(), 'Pos 4')]",
        "pos 5": "//div[contains(text(), 'Pos 5')]"
    }

    dfs = [collect_position_data(driver, role, xpath) for role, xpath in positions.items()]
    df_full_facets = pd.concat(dfs, axis=0)

    # Переименование колонок
    df_full_facets = df_full_facets.rename({
        "Hero": "hero",
        "Facet": "facet",
        "Matches": "matches",
        "Win Rate": "win_rate"
    }, axis=1)[["hero", "facet", "matches", "win_rate", "Role"]]

    # Очистка данных
    df_full_facets["win_rate"] = df_full_facets["win_rate"].apply(lambda x: x.replace("%", ""))
    df_full_facets = df_full_facets.convert_dtypes()

    logging.info("Сбор данных Facets завершен.")
    return df_full_facets
