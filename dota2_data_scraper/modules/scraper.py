import time
import pandas as pd
from bs4 import BeautifulSoup

def get_d2pt_page_table(driver):
    # Даем время на загрузку контента
    time.sleep(0.2)

    # Получаем HTML страницы
    page_source = driver.page_source

    # Парсим HTML с помощью BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')

    # Ищем строки таблицы по их CSS-классу
    table_rows = soup.find_all('div', class_='grid', style=True)

    # Список для хранения данных
    data = []
    headers = []

    for index, row in enumerate(table_rows):
        # Проверяем, чтобы строка не была заголовком
        cols = row.find_all('div', recursive=False)

        if index == 0:
            # Считаем первую строку заголовком
            for col in cols:
                header_text = col.get_text(strip=True)
                headers.append(header_text if header_text else None)
            continue

        row_data = []
        for col in cols:
            # Проверяем наличие изображений для извлечения роли
            img = col.find('img', alt=True)
            if img:
                row_data.append(img['alt'])
                continue

            # Обрабатываем содержимое внутри span
            spans = col.find_all('span')
            if spans:
                span_text = ' '.join([span.get_text(strip=True) for span in spans])
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
    df_heroes_table = df_heroes_table.dropna(how='all')

    # Очистка данных в процентах и диапазонах
    def clean_data(value):
        if isinstance(value, str):
            if '%' in value:
                try:
                    return float(value.replace('%', ''))
                except ValueError:
                    return value  # Вернуть исходное значение, если не удалось преобразовать
            elif '(' in value and ')' in value:
                try:
                    main_value, range_values = value.split('(')
                    main_value = main_value.strip()
                    range_values = range_values.replace(')', '').split('-')
                    return {
                        'main': int(main_value),
                        'range_min': int(range_values[0]),
                        'range_max': int(range_values[1])
                    }
                except ValueError:
                    return value  # Вернуть исходное значение, если формат не соответствует
        return value

    # Применяем очистку данных ко всем ячейкам
    df_heroes_table = df_heroes_table.applymap(clean_data)

    # Обработка типов данных для чисел
    df_heroes_table = df_heroes_table.apply(lambda x: pd.to_numeric(x, errors='ignore') if x.name != 2 else x)

    return df_heroes_table
