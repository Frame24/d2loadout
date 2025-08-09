"""
Модуль для оптимизации расположения элементов конфигурации
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ScreenDimensions:
    """Размеры экрана"""

    width: float = 1176.52
    height: float = 504.35
    margin: float = 4.35  # Минимальный отступ для предотвращения наложения


@dataclass
class CategoryLayout:
    """Компоновка категории"""

    name: str
    x: float
    y: float
    width: float
    height: float
    hero_count: int = 0
    priority: int = 1  # 1 - высокий, 2 - средний, 3 - низкий


class LayoutOptimizer:
    """Оптимизатор расположения элементов"""

    def __init__(self, screen: ScreenDimensions = None):
        self.screen = screen or ScreenDimensions()

    def calculate_optimal_layouts(self) -> Dict[str, List[CategoryLayout]]:
        """Вычисляет несколько оптимальных вариантов расположения"""

        layouts = {}

        # Вариант 1: Классическая сетка с оптимизированными размерами
        layouts["classic_optimized"] = self._create_classic_optimized_layout()

        # Вариант 2: Адаптивная сетка (больше места для популярных фасетов)
        layouts["adaptive_grid"] = self._create_adaptive_grid_layout()

        # Вариант 3: Компактное расположение с приоритетами
        layouts["compact_priority"] = self._create_compact_priority_layout()

        # Вариант 4: Горизонтальное расположение
        layouts["horizontal_flow"] = self._create_horizontal_flow_layout()

        # Вариант 5: Максимальное использование пространства
        layouts["space_maximized"] = self._create_space_maximized_layout()

        # Вариант 6: Полное использование пространства (100%)
        layouts["full_space_usage"] = self._create_full_space_layout()

        return layouts

    def _create_classic_optimized_layout(self) -> List[CategoryLayout]:
        """Классическая сетка с оптимизированными размерами - учитывает место для надписей"""
        layouts = []

        # Учитываем место для надписей категорий
        title_height = self.screen.margin * 2  # Возвращаем обычный отступ сверху

        # Отступ между блоками по вертикали
        vertical_gap = 30  # Тестовый отступ между блоками

        usable_height = (
            self.screen.height - title_height
        )  # Доступная высота без надписей

        # Основные фасеты (1 и 2) - используем 85% ширины для основной сетки
        main_area_width = self.screen.width * 0.85
        main_width = main_area_width / 5 - self.screen.margin  # ~195px
        # Уменьшаем высоту основных блоков с учетом увеличенного отступа между ними
        main_height = (
            usable_height / 2 - vertical_gap / 2
        )  # Учитываем больший отступ между рядами

        # Редкие фасеты (3+) - используем оставшиеся 15% ширины
        rare_width = self.screen.width * 0.15 - self.screen.margin  # ~172px
        # Уменьшаем высоту редких блоков с учетом отступов между ними
        rare_height = (
            usable_height / 5 - vertical_gap * 4 / 5
        )  # Учитываем 4 отступа между 5 блоками

        for pos in range(1, 6):
            # Фасет 1
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 1",
                    x=(main_width + self.screen.margin) * (pos - 1),
                    y=title_height,  # Отступ для надписи
                    width=main_width,
                    height=main_height,
                    priority=1,
                )
            )

            # Фасет 2
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 2",
                    x=(main_width + self.screen.margin) * (pos - 1),
                    y=title_height
                    + main_height
                    + vertical_gap,  # Используем новый отступ между рядами
                    width=main_width,
                    height=main_height,
                    priority=1,
                )
            )

            # Фасет 3+
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 3+",
                    x=main_area_width + self.screen.margin,
                    y=title_height
                    + (rare_height + vertical_gap)
                    * (pos - 1),  # Используем новый отступ между блоками
                    width=rare_width,
                    height=rare_height,
                    priority=3,
                )
            )

        return layouts

    def _create_adaptive_grid_layout(self) -> List[CategoryLayout]:
        """Адаптивная сетка - больше места популярным фасетам"""
        layouts = []

        # Фасеты 1 и 2 получают 85% ширины экрана
        main_area_width = self.screen.width * 0.85
        facet_width = main_area_width / 5 - self.screen.margin  # ~187px
        facet_height = (
            self.screen.height - self.screen.margin
        ) / 2 - self.screen.margin  # ~265px

        # Фасеты 3+ получают оставшиеся 15%
        rare_area_width = self.screen.width * 0.15 - self.screen.margin
        rare_height = self.screen.height / 5 - self.screen.margin  # ~94px

        for pos in range(1, 6):
            # Фасет 1 - верхний ряд
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 1",
                    x=(facet_width + self.screen.margin) * (pos - 1),
                    y=0,
                    width=facet_width,
                    height=facet_height,
                    priority=1,
                )
            )

            # Фасет 2 - нижний ряд
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 2",
                    x=(facet_width + self.screen.margin) * (pos - 1),
                    y=facet_height + self.screen.margin,
                    width=facet_width,
                    height=facet_height,
                    priority=1,
                )
            )

            # Фасет 3+ - правая колонка
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 3+",
                    x=main_area_width + self.screen.margin,
                    y=rare_height * (pos - 1) + self.screen.margin * (pos - 1),
                    width=rare_area_width,
                    height=rare_height,
                    priority=3,
                )
            )

        return layouts

    def _create_compact_priority_layout(self) -> List[CategoryLayout]:
        """Компактное расположение с учетом приоритетов - 100% использования"""
        layouts = []

        # Используем 90% ширины для популярных фасетов
        main_area_width = self.screen.width * 0.90
        high_priority_width = main_area_width / 5 - self.screen.margin  # ~207px
        high_priority_height = self.screen.height / 2 - self.screen.margin  # ~248px

        # Оставшиеся 10% для редких фасетов
        rare_area_width = self.screen.width * 0.10 - self.screen.margin  # ~113px
        low_priority_height = self.screen.height / 5 - self.screen.margin  # ~96px

        # Располагаем фасеты 1 и 2 в основной области
        for pos in range(1, 6):
            # Фасет 1
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 1",
                    x=(high_priority_width + self.screen.margin) * (pos - 1),
                    y=0,
                    width=high_priority_width,
                    height=high_priority_height,
                    priority=1,
                )
            )

            # Фасет 2
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 2",
                    x=(high_priority_width + self.screen.margin) * (pos - 1),
                    y=high_priority_height + self.screen.margin,
                    width=high_priority_width,
                    height=high_priority_height,  # Такой же размер как у фасета 1
                    priority=1,
                )
            )

        # Фасеты 3+ размещаем в правой колонке
        for pos in range(1, 6):
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 3+",
                    x=main_area_width + self.screen.margin,
                    y=(low_priority_height + self.screen.margin) * (pos - 1),
                    width=rare_area_width,
                    height=low_priority_height,
                    priority=3,
                )
            )

        return layouts

    def _create_horizontal_flow_layout(self) -> List[CategoryLayout]:
        """Горизонтальное расположение по потоку"""
        layouts = []

        # Все категории одинакового размера, но разной важности
        categories_per_row = 6
        category_width = (
            self.screen.width - self.screen.margin * (categories_per_row + 1)
        ) / categories_per_row
        category_height = 140

        categories = []

        # Создаем список всех категорий с приоритетами
        for pos in range(1, 6):
            categories.extend(
                [
                    (f"POS {pos} F 1", 1),  # Высокий приоритет
                    (f"POS {pos} F 2", 1),  # Высокий приоритет
                    (f"POS {pos} F 3+", 3),  # Низкий приоритет
                ]
            )

        # Сортируем по приоритету
        categories.sort(key=lambda x: x[1])

        # Размещаем в горизонтальном потоке
        for i, (name, priority) in enumerate(categories):
            row = i // categories_per_row
            col = i % categories_per_row

            # Для редких фасетов уменьшаем высоту
            height = category_height if priority <= 2 else category_height * 0.6

            layouts.append(
                CategoryLayout(
                    name=name,
                    x=col * (category_width + self.screen.margin) + self.screen.margin,
                    y=row * (category_height + self.screen.margin) + self.screen.margin,
                    width=category_width,
                    height=height,
                    priority=priority,
                )
            )

        return layouts

    def _create_space_maximized_layout(self) -> List[CategoryLayout]:
        """Максимальное использование доступного пространства"""
        layouts = []

        # Вычисляем оптимальные размеры для максимального заполнения
        total_categories = 15  # 5 позиций × 3 фасета

        # Популярные фасеты (1 и 2) получают 75% площади
        popular_area = self.screen.width * self.screen.height * 0.75
        popular_count = 10  # 5 позиций × 2 фасета
        popular_area_per_item = popular_area / popular_count

        # Редкие фасеты (3+) получают 25% площади
        rare_area = self.screen.width * self.screen.height * 0.25
        rare_count = 5
        rare_area_per_item = rare_area / rare_count

        # Рассчитываем размеры для популярных фасетов
        popular_width = math.sqrt(popular_area_per_item * 1.2)  # Делаем шире
        popular_height = popular_area_per_item / popular_width

        # Рассчитываем размеры для редких фасетов
        rare_width = math.sqrt(rare_area_per_item * 0.8)  # Делаем уже
        rare_height = rare_area_per_item / rare_width

        # Размещаем популярные фасеты в сетке 5x2
        cols_popular = 5
        rows_popular = 2

        for pos in range(1, 6):
            for facet in [1, 2]:
                row = facet - 1
                col = pos - 1

                layouts.append(
                    CategoryLayout(
                        name=f"POS {pos} F {facet}",
                        x=col * (popular_width + self.screen.margin),
                        y=row * (popular_height + self.screen.margin),
                        width=popular_width,
                        height=popular_height,
                        priority=1,
                    )
                )

        # Размещаем редкие фасеты в оставшемся пространстве
        start_x = 5 * (popular_width + self.screen.margin)
        available_width = self.screen.width - start_x

        for pos in range(1, 6):
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 3+",
                    x=start_x,
                    y=(pos - 1) * (rare_height + self.screen.margin),
                    width=min(rare_width, available_width - self.screen.margin),
                    height=rare_height,
                    priority=3,
                )
            )

        return layouts

    def _create_full_space_layout(self) -> List[CategoryLayout]:
        """Полное использование пространства (100%) без отступов"""
        layouts = []

        # Популярные фасеты занимают 4 колонки из 5
        popular_columns = 4
        rare_columns = 1

        popular_width = self.screen.width * (popular_columns / 5)  # 80% ширины
        rare_width = self.screen.width * (rare_columns / 5)  # 20% ширины

        # Каждая популярная колонка делится на 2 ряда
        facet_width = popular_width / popular_columns  # Ширина одного фасета
        facet_height = self.screen.height / 2  # Высота фасета

        # Редкие фасеты - 5 рядов
        rare_height = self.screen.height / 5

        # Размещаем популярные фасеты (1 и 2) в первых 4 колонках
        for pos in range(1, 5):  # Только позиции 1-4, позиция 5 будет в редких
            # Фасет 1 - верхний ряд
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 1",
                    x=(pos - 1) * facet_width,
                    y=0,
                    width=facet_width,
                    height=facet_height,
                    priority=1,
                )
            )

            # Фасет 2 - нижний ряд
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 2",
                    x=(pos - 1) * facet_width,
                    y=facet_height,
                    width=facet_width,
                    height=facet_height,
                    priority=1,
                )
            )

        # Правая колонка для всех редких фасетов и позиции 5
        right_column_x = popular_width

        # Позиция 5 фасеты 1 и 2 - занимают верхние 2/5 правой колонки
        pos5_height = self.screen.height * 2 / 5
        layouts.append(
            CategoryLayout(
                name="POS 5 F 1",
                x=right_column_x,
                y=0,
                width=rare_width,
                height=pos5_height / 2,
                priority=1,
            )
        )

        layouts.append(
            CategoryLayout(
                name="POS 5 F 2",
                x=right_column_x,
                y=pos5_height / 2,
                width=rare_width,
                height=pos5_height / 2,
                priority=1,
            )
        )

        # Все фасеты 3+ занимают нижние 3/5 правой колонки
        rare_start_y = pos5_height
        rare_section_height = self.screen.height - pos5_height
        rare_facet_height = rare_section_height / 5

        for pos in range(1, 6):
            layouts.append(
                CategoryLayout(
                    name=f"POS {pos} F 3+",
                    x=right_column_x,
                    y=rare_start_y + (pos - 1) * rare_facet_height,
                    width=rare_width,
                    height=rare_facet_height,
                    priority=3,
                )
            )

        return layouts

    def get_layout_stats(self, layout: List[CategoryLayout]) -> Dict[str, float]:
        """Получает статистику использования пространства для макета"""
        total_area = self.screen.width * self.screen.height
        used_area = sum(cat.width * cat.height for cat in layout)

        high_priority_area = sum(
            cat.width * cat.height for cat in layout if cat.priority == 1
        )
        low_priority_area = sum(
            cat.width * cat.height for cat in layout if cat.priority == 3
        )

        return {
            "total_usage_percent": (used_area / total_area) * 100,
            "high_priority_percent": (high_priority_area / used_area) * 100,
            "low_priority_percent": (low_priority_area / used_area) * 100,
            "wasted_space_percent": ((total_area - used_area) / total_area) * 100,
        }

    def print_layout_comparison(self, layouts: Dict[str, List[CategoryLayout]]):
        """Выводит сравнение различных макетов"""
        print(f"\n{'='*80}")
        print("СРАВНЕНИЕ МАКЕТОВ КОНФИГУРАЦИИ")
        print(f"{'='*80}")
        print(
            f"Доступное пространство: {self.screen.width}x{self.screen.height} = {self.screen.width * self.screen.height} пикселей"
        )
        print(f"{'='*80}")

        for name, layout in layouts.items():
            stats = self.get_layout_stats(layout)

            print(f"\n📐 {name.upper().replace('_', ' ')}")
            print(f"   Использование пространства: {stats['total_usage_percent']:.1f}%")
            print(
                f"   Популярные фасеты (1-2):    {stats['high_priority_percent']:.1f}%"
            )
            print(
                f"   Редкие фасеты (3+):         {stats['low_priority_percent']:.1f}%"
            )
            print(
                f"   Потери пространства:        {stats['wasted_space_percent']:.1f}%"
            )

            # Показываем размеры типичных элементов
            high_priority_items = [cat for cat in layout if cat.priority == 1]
            low_priority_items = [cat for cat in layout if cat.priority == 3]

            if high_priority_items:
                avg_hp_size = sum(
                    cat.width * cat.height for cat in high_priority_items
                ) / len(high_priority_items)
                print(f"   Средний размер популярных:  {avg_hp_size:.0f} пикселей")

            if low_priority_items:
                avg_lp_size = sum(
                    cat.width * cat.height for cat in low_priority_items
                ) / len(low_priority_items)
                print(f"   Средний размер редких:      {avg_lp_size:.0f} пикселей")
