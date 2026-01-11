"""
Тесты проверки XPath селекторов
Проверяют что селекторы для позиций работают корректно
Оптимизированы с общими фикстурами
"""

import pytest
from bs4 import BeautifulSoup

pytestmark = pytest.mark.slow


class TestXPathSelectors:
    """Тесты XPath селекторов для позиций - оптимизированы"""

    def test_all_positions_xpath_and_clickable(self, browser_manager):
        """
        Комплексный тест XPath селекторов для всех позиций:
        - Проверка наличия элементов в HTML
        - Проверка кликабельности
        """
        positions = {
            "Carry": "//div[contains(text(), 'Carry')]",
            "Mid": "//div[contains(text(), 'Mid')]",
            "Offlane": "//div[contains(text(), 'Off')]",
            "Pos 4": "//div[contains(text(), 'Pos 4')]",
            "Pos 5": "//div[contains(text(), 'Pos 5')]",
        }
        
        page_source = browser_manager.get_page_source()
        soup = BeautifulSoup(page_source, "html.parser")
        
        # Проверяем наличие элементов в HTML и кликабельность
        failed_positions = []
        for pos_name, xpath in positions.items():
            # Проверка в HTML
            search_text = pos_name if pos_name not in ["Offlane", "Pos 4", "Pos 5"] else (
                "Off" if pos_name == "Offlane" else pos_name
            )
            elements = soup.find_all("div", string=lambda text: text and search_text in text)
            assert len(elements) > 0, f"Элемент с текстом '{search_text}' не найден"
            
            # Проверка кликабельности
            result = browser_manager.click_element_safely(xpath, timeout=15)
            if not result:
                failed_positions.append(pos_name)
        
        assert len(failed_positions) == 0, f"Не удалось кликнуть по позициям: {failed_positions}"
