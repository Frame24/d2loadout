# Тесты для d2loadout

## Структура

- `test/d2loadoutUnit/` - модульные тесты (границы модулей)
- `test/d2loadoutIntegration/` - интеграционные тесты (фактическая работа скрапера)

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### Только интеграционные тесты (проверка работы скрапера)
```bash
pytest test/d2loadoutIntegration/
```

### Только модульные тесты
```bash
pytest test/d2loadoutUnit/
```

### Конкретный модуль
```bash
pytest test/d2loadoutUnit/core/
pytest test/d2loadoutUnit/scrapers/
pytest test/d2loadoutUnit/utils/
```

### Конкретный файл
```bash
pytest test/d2loadoutUnit/core/test_data_manager.py
```

### С покрытием кода
```bash
pytest --cov=dota2_data_scraper --cov-report=html
```

### Пропустить медленные интеграционные тесты
```bash
pytest -m "not slow"
```

## Структура тестов

### Модульные тесты (`d2loadoutUnit/`)
- `core/` - тесты для модулей core (DataManager, ConfigProcessor)
- `scrapers/` - тесты для скраперов (HeroScraper)
- `utils/` - тесты для утилит (FacetAPIParser)

### Интеграционные тесты (`d2loadoutIntegration/`)
- `test_scraper_integration.py` - проверка работы с реальным сайтом
- `test_data_extraction.py` - проверка извлечения данных из HTML
- `test_xpath_selectors.py` - проверка XPath селекторов

## Принципы тестирования

### Модульные тесты
Тесты написаны только для границ модулей:
- Публичные API методов
- Взаимодействие с внешними системами (моки)
- Сохранение/загрузка данных
- Обработка ошибок на границах

Внутренняя логика не тестируется.

### Интеграционные тесты
Проверяют фактическую работу скрапера:
- Загрузка страниц
- Наличие элементов на странице
- Работа XPath селекторов
- Извлечение данных из HTML
- Структура полученных данных
- **Сохранение промежуточных результатов для сравнения с сайтом**

**Важно**: Интеграционные тесты работают с реальным сайтом и могут быть медленными. Они помогают быстро обнаружить изменения верстки сайта.

## Просмотр промежуточных результатов

Тесты сохраняют спарсенные данные в папку `test_output/` для сравнения с сайтом:

### Запуск теста с сохранением данных одной позиции:
```bash
.\venv\Scripts\activate
pytest test/d2loadoutIntegration/test_actual_data_validation.py::TestActualDataValidation::test_scraped_data_contains_real_heroes -v -s
```

### Запуск теста для всех позиций:
```bash
.\venv\Scripts\activate
pytest test/d2loadoutIntegration/test_all_positions_comparison.py -v -s
```

### Сравнение с сайтом:
1. Запустите тест - данные сохранятся в `test_output/*.csv`
2. Откройте сайт: https://dota2protracker.com/meta
3. Выберите ту же позицию что в тесте
4. Сравните данные в CSV файле с данными на сайте
5. Проверьте:
   - Имена героев совпадают
   - Статистика (матчи, WR) совпадает
   - Фасеты извлекаются корректно
   - Порядок героев соответствует сайту

### Формат сохраненных данных:
- CSV файлы с UTF-8 кодировкой (открываются в Excel)
- Полная таблица как на сайте
- Все колонки: Hero, Facet, facet_number, Matches, WR, D2PT Rating и т.д.
- В консоли выводится таблица и статистика для быстрой проверки

### Проверка соответствия фасетов и номеров:
```bash
.\venv\Scripts\activate
pytest test/d2loadoutIntegration/test_facet_number_validation.py -v -s
```

Эти тесты:
- Вычисляют номера фасетов (как в реальном коде)
- Сохраняют таблицу Hero | Facet | facet_number в CSV
- Выводят таблицу в консоль для визуальной проверки
- Группируют фасеты по героям для проверки соответствия

Файлы сохраняются в `test_output/facet_numbers_*.csv` - можно открыть в Excel и проверить что номера соответствуют именам фасетов.
