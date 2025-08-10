"""
Скрапер для сбора данных о героях Dota 2
"""

import pandas as pd
import time
import logging
from typing import Dict, List
from bs4 import BeautifulSoup

from ..core.scraping_manager import ScrapingManager
from ..utils.facet_api_parser import FacetAPIParser

logger = logging.getLogger(__name__)


class HeroScraper:
    """Скрапер для сбора данных о героях"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.positions = {
            "Carry (pos 1)": "//div[contains(text(), 'Carry')]",
            "Mid (pos 2)": "//div[contains(text(), 'Mid')]",
            "Offlaner (pos 3)": "//div[contains(text(), 'Off')]",
            "Support (pos 4)": "//div[contains(text(), 'Pos 4')]",
            "Hard Support (pos 5)": "//div[contains(text(), 'Pos 5')]",
        }
        # Маппинг для коротких названий в данных
        self.role_mapping = {
            "Carry (pos 1)": "pos 1",
            "Mid (pos 2)": "pos 2",
            "Offlaner (pos 3)": "pos 3",
            "Support (pos 4)": "pos 4",
            "Hard Support (pos 5)": "pos 5",
        }
        self.facet_parser = FacetAPIParser()

    def scrape_heroes_data(
        self, url: str = "https://dota2protracker.com/meta", show_progress: bool = False
    ) -> pd.DataFrame:
        """
        Сбор данных о героях

        Args:
            url: URL страницы с данными
            show_progress: Показывать прогресс парсинга позиций

        Returns:
            DataFrame с данными о героях
        """
        logger.info("Начало сбора данных о героях...")

        with ScrapingManager(headless=self.headless) as manager:
            manager.navigate_to_page(url)

            dfs = []

            # Проход по всем позициям и сбор данных
            positions_list = list(self.positions.items())
            for i, (position, xpath) in enumerate(positions_list, 1):
                if show_progress:
                    print(f"   📍 Позиция {i}/5: {position}")
                logger.info(f"Сбор данных для {position}")

                # Кликаем по позиции
                if manager.click_element_safely(xpath):
                    # Получаем данные таблицы
                    df = self._extract_table_data(manager.driver)
                    df["Role"] = self.role_mapping[position]
                    dfs.append(df)
                else:
                    logger.error(f"Не удалось кликнуть по позиции {position}")

            if dfs:
                df_full = pd.concat(dfs, axis=0, ignore_index=True)

                # Обеспечиваем наличие имени фасета и корректного номера фасета
                df_full = self._ensure_facet_names_and_numbers(df_full)

                # В heroes_data.csv оставляем только имя фасета, номер не сохраняем
                if "facet_number" in df_full.columns:
                    df_full = df_full.drop(columns=["facet_number"])

                logger.info("Сбор данных о героях завершен")
                return df_full
            else:
                logger.error("Не удалось собрать данные о героях")
                return pd.DataFrame()

    def scrape_heroes_no_facets(
        self, url: str = "https://dota2protracker.com/meta"
    ) -> pd.DataFrame:
        """
        Сбор данных о героях без разделения по фасетам (группировка фасетов)

        Args:
            url: URL страницы с данными

        Returns:
            DataFrame с данными о героях без фасетов
        """
        logger.info("Начало сбора данных о героях без фасетов...")

        with ScrapingManager(headless=self.headless) as manager:
            manager.navigate_to_page(url)

            # Сначала собираем данные с фасетами
            dfs_with_facets = []
            for position, xpath in self.positions.items():
                logger.info(f"Сбор данных с фасетами для {position}")

                if manager.click_element_safely(xpath):
                    df = self._extract_table_data(manager.driver)
                    df["Role"] = self.role_mapping[position]
                    dfs_with_facets.append(df)

            # После pos 5 включаем группировку фасетов
            logger.info("Переключение на группировку фасетов...")

            # Ищем кнопку переключения группировки фасетов
            # Попробуем разные селекторы
            possible_selectors = [
                'button[role="switch"][aria-checked="false"]',
                'button[role="switch"]',
                '[role="switch"]',
                "button.svelte-9e5jyr",
                ".svelte-9e5jyr",
            ]

            facet_toggle = None
            for selector in possible_selectors:
                try:
                    elements = manager.driver.find_elements("css selector", selector)
                    logger.info(
                        f"Найдено {len(elements)} элементов с селектором: {selector}"
                    )

                    for element in elements:
                        # Проверяем, что это кнопка переключения фасетов
                        if element.get_attribute("role") == "switch":
                            facet_toggle = element
                            logger.info(f"✅ Найдена кнопка переключения: {selector}")
                            break

                    if facet_toggle:
                        break

                except Exception as e:
                    logger.debug(f"Селектор {selector} не сработал: {e}")
                    continue

            if facet_toggle:
                try:
                    # Проверяем текущее состояние
                    is_checked = facet_toggle.get_attribute("aria-checked") == "true"
                    logger.info(
                        f"Текущее состояние группировки фасетов: {'включена' if is_checked else 'отключена'}"
                    )

                    # Если группировка еще не включена, включаем
                    if not is_checked:
                        manager.driver.execute_script(
                            "arguments[0].click();", facet_toggle
                        )
                        logger.info("✅ Группировка фасетов включена")
                        time.sleep(3)  # Ждем обновления данных
                    else:
                        logger.info("Группировка фасетов уже была включена")

                except Exception as e:
                    logger.warning(f"Ошибка при переключении группировки фасетов: {e}")
                    return pd.DataFrame()
            else:
                logger.warning("Не удалось найти кнопку группировки фасетов")
                return pd.DataFrame()

            # Теперь собираем данные без фасетов
            dfs_no_facets = []
            for position, xpath in self.positions.items():
                logger.info(f"Сбор данных без фасетов для {position}")

                if manager.click_element_safely(xpath):
                    df = self._extract_table_data(manager.driver)
                    df["Role"] = self.role_mapping[position]
                    df["Facet"] = "No Facet"  # Указываем что это данные без фасетов
                    dfs_no_facets.append(df)

            if dfs_no_facets:
                df_no_facets = pd.concat(dfs_no_facets, axis=0, ignore_index=True)
                logger.info("Сбор данных о героях без фасетов завершен")
                return df_no_facets
            else:
                logger.error("Не удалось собрать данные о героях без фасетов")
                return pd.DataFrame()

    def scrape_both_data_types(
        self, url: str = "https://dota2protracker.com/meta", show_progress: bool = False
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Эффективный сбор обоих типов данных за один проход браузера

        Args:
            url: URL страницы с данными
            show_progress: Показывать прогресс парсинга позиций

        Returns:
            tuple: (DataFrame с фасетами, DataFrame без фасетов)
        """
        logger.info("Начало эффективного сбора данных (оба типа)...")

        with ScrapingManager(headless=self.headless) as manager:
            manager.navigate_to_page(url)

            # Сначала собираем данные с фасетами
            logger.info("Сбор данных с фасетами...")
            dfs_with_facets = []

            positions_list = list(self.positions.items())
            for i, (position, xpath) in enumerate(positions_list, 1):
                if show_progress:
                    print(f"   📍 Позиция {i}/5: {position}")
                logger.info(f"Сбор данных с фасетами для {position}")

                if manager.click_element_safely(xpath):
                    df = self._extract_table_data(manager.driver)
                    df["Role"] = self.role_mapping[position]
                    dfs_with_facets.append(df)
                else:
                    logger.error(f"Не удалось кликнуть по позиции {position}")

            # Обрабатываем данные с фасетами
            df_with_facets = pd.DataFrame()
            if dfs_with_facets:
                df_with_facets = pd.concat(dfs_with_facets, axis=0, ignore_index=True)
                df_with_facets = self._ensure_facet_names_and_numbers(df_with_facets)

                # В heroes_data.csv оставляем только имя фасета, номер не сохраняем
                if "facet_number" in df_with_facets.columns:
                    df_with_facets = df_with_facets.drop(columns=["facet_number"])

                logger.info("Сбор данных с фасетами завершен")
            else:
                logger.error("Не удалось собрать данные с фасетами")

            # Теперь переключаемся на группировку фасетов и собираем данные без фасетов
            logger.info("Переключение на группировку фасетов...")

            # Ищем кнопку переключения группировки фасетов
            possible_selectors = [
                'button[role="switch"][aria-checked="false"]',
                'button[role="switch"]',
                '[role="switch"]',
                "button.svelte-9e5jyr",
                ".svelte-9e5jyr",
            ]

            facet_toggle = None
            for selector in possible_selectors:
                try:
                    elements = manager.driver.find_elements("css selector", selector)
                    logger.info(
                        f"Найдено {len(elements)} элементов с селектором: {selector}"
                    )

                    for element in elements:
                        if element.get_attribute("role") == "switch":
                            facet_toggle = element
                            logger.info(f"✅ Найдена кнопка переключения: {selector}")
                            break

                    if facet_toggle:
                        break

                except Exception as e:
                    logger.debug(f"Селектор {selector} не сработал: {e}")
                    continue

            df_no_facets = pd.DataFrame()
            if facet_toggle:
                try:
                    # Проверяем текущее состояние
                    is_checked = facet_toggle.get_attribute("aria-checked") == "true"
                    logger.info(
                        f"Текущее состояние группировки фасетов: {'включена' if is_checked else 'отключена'}"
                    )

                    # Если группировка еще не включена, включаем
                    if not is_checked:
                        manager.driver.execute_script(
                            "arguments[0].click();", facet_toggle
                        )
                        logger.info("✅ Группировка фасетов включена")
                        time.sleep(3)  # Ждем обновления данных
                    else:
                        logger.info("Группировка фасетов уже была включена")

                        # Собираем данные без фасетов
                    logger.info("Сбор данных без фасетов...")
                    if show_progress:
                        print("   🔄 Переключились на группировку фасетов")
                    dfs_no_facets = []

                    for i, (position, xpath) in enumerate(positions_list, 1):
                        if show_progress:
                            print(f"   📍 Позиция {i}/5: {position} (без фасетов)")
                        logger.info(f"Сбор данных без фасетов для {position}")

                        if manager.click_element_safely(xpath):
                            df = self._extract_table_data(manager.driver)
                            df["Role"] = self.role_mapping[position]
                            df["Facet"] = (
                                "No Facet"  # Указываем что это данные без фасетов
                            )
                            dfs_no_facets.append(df)

                    if dfs_no_facets:
                        df_no_facets = pd.concat(
                            dfs_no_facets, axis=0, ignore_index=True
                        )
                        logger.info("Сбор данных без фасетов завершен")
                    else:
                        logger.error("Не удалось собрать данные без фасетов")

                except Exception as e:
                    logger.warning(f"Ошибка при переключении группировки фасетов: {e}")
            else:
                logger.warning("Не удалось найти кнопку группировки фасетов")

            logger.info("Эффективный сбор данных завершен")
            return df_with_facets, df_no_facets

    def _ensure_facet_names_and_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Гарантирует наличие колонки 'Facet' (имя фасета). Если имя отсутствует,
        пытаемся восстановить его по порядковому номеру и маппингу. Также
        вычисляем корректный 'facet_number' на основе имени, если возможно.
        """
        logger.info("Обеспечение корректных имен и номеров фасетов...")

        # Получаем маппинг: hero_name -> {facet_name: order}
        facets_mapping = self.facet_parser.get_hero_facets_mapping()
        logger.info(f"Получен маппинг фасетов для {len(facets_mapping)} героев")

        facet_names: list[str] = []
        facet_numbers: list[int] = []

        # Предрассчитываем порядковый номер появления в рамках (Hero, Role)
        try:
            order_by_idx = (
                df.reset_index()
                .groupby([df["Hero"], df["Role"]])
                .cumcount()
                .rename("_order")
            )
            # Поскольку мы использовали reset_index, сопоставим обратно по исходному индексу
            order_series = pd.Series(order_by_idx.values, index=order_by_idx.index)
        except Exception:
            order_series = pd.Series(0, index=df.index)

        def is_valid_facet_name(val: object) -> bool:
            if not isinstance(val, str):
                return False
            s = val.strip()
            if not s:
                return False
            # Чисто числовые/"3+"/"Facet 1" считаем неименованными
            if s.isdigit() or s in {"1", "2", "3", "3+"}:
                return False
            import re as _re

            if _re.match(r"^Facet\s*\d+\+?$", s, flags=_re.IGNORECASE):
                return False
            # Имена обычно содержат буквы; допустим как валид.
            return any(ch.isalpha() for ch in s)

        for idx, row in df.iterrows():
            hero_name = row.get("Hero")
            role_value = row.get("Role")

            # 1) Базовое имя фасета, если оно есть в таблице
            name: str | None = row.get("Facet") if "Facet" in df.columns else None

            # 2) Если нет имени, пробуем определить порядковый номер строки для героя/роли
            #    и найти имя через инверсию маппинга name->order
            fallback_order: int | None = None
            # Позиция текущей строки внутри среза (1-based)
            try:
                # Находим порядковый номер для текущего индекса
                # Если вычислить не удается — примем 0
                fallback_order = int(order_series.get(idx, 0)) + 1
            except Exception:
                fallback_order = 1

            # Если name отсутствует или выглядит как номер, пробуем заменить на настоящее имя
            if not is_valid_facet_name(name):
                if isinstance(hero_name, str):
                    name_to_order = facets_mapping.get(hero_name, {})
                    if not name_to_order:
                        # Получим маппинг только для этого героя
                        name_to_order = self.facet_parser.get_name_to_order_for_hero(
                            hero_name
                        )
                    order_to_name = {v: k for k, v in name_to_order.items()}
                    resolved = order_to_name.get(fallback_order)
                    if isinstance(resolved, str) and resolved.strip():
                        name = resolved
                    else:
                        name = f"Facet {fallback_order}"

            # 3) Вычисляем номер фасета по имени, если это возможно
            number: int | None = None
            if isinstance(hero_name, str) and isinstance(name, str):
                name_to_order = facets_mapping.get(hero_name, {})
                number = name_to_order.get(name)
                # Если не нашли в общей карте — пробуем получить маппинг только для этого героя
                if number is None:
                    name_to_order = self.facet_parser.get_name_to_order_for_hero(
                        hero_name
                    )
                    number = name_to_order.get(name)

            # 4) Фолбек: если номер не найден, используем ранее вычисленный fallback_order
            if number is None:
                number = fallback_order if fallback_order is not None else 1

            facet_names.append(name if isinstance(name, str) else f"Facet {number}")
            facet_numbers.append(int(number))

        # Обновляем/создаем колонки
        df["Facet"] = facet_names
        df["facet_number"] = facet_numbers

        # Переставляем колонки: Hero, Facet, facet_number рядом
        cols = list(df.columns)
        try:
            hero_idx = cols.index("Hero")
            # Удаляем и вставляем Facet сразу после Hero
            if "Facet" in cols:
                cols.insert(hero_idx + 1, cols.pop(cols.index("Facet")))
            if "facet_number" in cols:
                cols.insert(hero_idx + 2, cols.pop(cols.index("facet_number")))
            df = df[cols]
        except ValueError:
            pass

        logger.info(f"Добавлены имена и номера фасетов для {len(df)} записей")
        return df

    def _extract_table_data(self, driver) -> pd.DataFrame:
        """
        Извлечение данных из таблицы

        Args:
            driver: WebDriver instance

        Returns:
            DataFrame с данными таблицы
        """
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
        facet_col_index = -1
        hero_col_index = -1

        for index, row in enumerate(table_rows):
            # Проверяем, чтобы строка не была заголовком
            cols = row.find_all("div", recursive=False)

            if index == 0:
                # Считаем первую строку заголовком
                for col in cols:
                    header_text = col.get_text(strip=True)
                    headers.append(header_text if header_text else None)
                try:
                    facet_col_index = headers.index("Facet")
                except ValueError:
                    facet_col_index = -1
                try:
                    hero_col_index = headers.index("Hero")
                except ValueError:
                    hero_col_index = -1
                # Если 'Facet' не объявлен в заголовках, добавим его сразу после 'Hero'
                if hero_col_index != -1 and "Facet" not in headers:
                    headers.insert(hero_col_index + 1, "Facet")
                    # Обновим индексы после вставки
                    facet_col_index = hero_col_index + 1
                continue

            row_data = []
            for col_idx, col in enumerate(cols):
                # Если это колонка героя — извлекаем имя героя и имя фасета из tooltip
                if hero_col_index != -1 and col_idx == hero_col_index:
                    # Имя героя (alt у img или текст)
                    hero_name = None
                    hero_img = col.find("img", alt=True)
                    if hero_img and isinstance(hero_img.get("alt"), str):
                        hero_name = hero_img.get("alt").strip()
                    if not hero_name:
                        hero_name = col.get_text(strip=True) or None
                    row_data.append(hero_name if hero_name else None)

                    # Имя фасета — внутри блока tooltip (класс font-bold)
                    facet_name = None
                    try:
                        for d in col.find_all("div", class_=True):
                            classes = d.get("class", [])
                            if isinstance(classes, list) and "font-bold" in classes:
                                text_val = d.get_text(strip=True)
                                if text_val:
                                    facet_name = text_val
                                    break
                    except Exception:
                        facet_name = None
                    if not facet_name:
                        # Фолбек: любые элементы с атрибутами title/data-tip/aria-label
                        tip_el = col.find(attrs={"data-tip": True})
                        if tip_el and isinstance(tip_el.get("data-tip"), str):
                            facet_name = tip_el.get("data-tip").strip()
                    if not facet_name:
                        title_el = col.find(attrs={"title": True})
                        if title_el and isinstance(title_el.get("title"), str):
                            facet_name = title_el.get("title").strip()
                    if not facet_name:
                        aria_el = col.find(attrs={"aria-label": True})
                        if aria_el and isinstance(aria_el.get("aria-label"), str):
                            facet_name = aria_el.get("aria-label").strip()
                    if not facet_name:
                        span_text = " ".join(
                            [s.get_text(strip=True) for s in col.find_all("span")]
                        )
                        facet_name = (
                            span_text if span_text else col.get_text(strip=True) or None
                        )

                    # Вставляем имя фасета сразу после имени героя
                    row_data.append(facet_name if facet_name else None)
                    continue

                # Специальная обработка колонки Facet: пытаемся достать имя фасета
                if facet_col_index != -1 and col_idx == facet_col_index:
                    facet_name = None
                    # Приоритет: data-tip -> title -> aria-label -> текст
                    tip_el = col.find(attrs={"data-tip": True})
                    if tip_el and isinstance(tip_el.get("data-tip"), str):
                        facet_name = tip_el.get("data-tip").strip()
                    if not facet_name:
                        title_el = col.find(attrs={"title": True})
                        if title_el and isinstance(title_el.get("title"), str):
                            facet_name = title_el.get("title").strip()
                    if not facet_name:
                        aria_el = col.find(attrs={"aria-label": True})
                        if aria_el and isinstance(aria_el.get("aria-label"), str):
                            facet_name = aria_el.get("aria-label").strip()
                    if not facet_name:
                        # Падает в текстовое содержимое (могут быть вложенные span)
                        span_text = " ".join(
                            [s.get_text(strip=True) for s in col.find_all("span")]
                        )
                        facet_name = (
                            span_text if span_text else col.get_text(strip=True) or None
                        )
                    row_data.append(facet_name if facet_name else None)
                    continue

                # Проверяем наличие изображений для извлечения роли/имени
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
        df_heroes_table = self._clean_data(df_heroes_table)

        return df_heroes_table

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Очистка данных в DataFrame

        Args:
            df: DataFrame для очистки

        Returns:
            Очищенный DataFrame
        """

        def clean_data(value):
            if isinstance(value, str):
                if "%" in value:
                    try:
                        return float(value.replace("%", ""))
                    except ValueError:
                        return value
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
                        return value
            return value

        # Применяем очистку данных ко всем ячейкам
        df = df.map(clean_data)

        # Обработка типов данных для чисел
        df = df.apply(lambda x: x.convert_dtypes() if x.name != 2 else x)

        return df
