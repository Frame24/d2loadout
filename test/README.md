# Тесты для d2loadout (lite)

## Структура

- `test/d2loadoutUnit/` - модульные тесты (границы модулей)

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### Только модульные тесты
```bash
pytest test/d2loadoutUnit/
```

### Конкретный модуль
```bash
pytest test/d2loadoutUnit/core/
pytest test/d2loadoutUnit/scrapers/
```

### Конкретный файл
```bash
pytest test/d2loadoutUnit/core/test_data_manager.py
```

### С покрытием кода
```bash
pytest --cov=dota2_data_scraper --cov-report=html
```

## Структура тестов

### Модульные тесты (`d2loadoutUnit/`)
- `core/` - DataManager, ConfigProcessor
- `scrapers/` - hero_stats_api (D2PT API)

## Принципы тестирования

Тесты написаны для границ модулей:
- Публичные API методов
- Взаимодействие с внешними системами (моки)
- Сохранение/загрузка данных
- Обработка ошибок на границах

Внутренняя логика не тестируется.
