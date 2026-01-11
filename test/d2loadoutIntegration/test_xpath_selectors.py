"""
Тесты проверки XPath селекторов
Проверяют что селекторы для позиций работают корректно
"""

import pytest

pytestmark = pytest.mark.slow
from dota2_data_scraper.modules.core.scraping_manager import ScrapingManager
from bs4 import BeautifulSoup


class TestXPathSelectors:
    """Тесты XPath селекторов для позиций"""

    def test_carry_position_xpath(self):
        """Тест XPath для позиции Carry"""
        xpath = "//div[contains(text(), 'Carry')]"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            
            soup = BeautifulSoup(page_source, "html.parser")
            elements = soup.find_all("div", string=lambda text: text and "Carry" in text)
            
            assert len(elements) > 0, "Элемент с текстом 'Carry' не найден"

    def test_mid_position_xpath(self):
        """Тест XPath для позиции Mid"""
        xpath = "//div[contains(text(), 'Mid')]"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            
            soup = BeautifulSoup(page_source, "html.parser")
            elements = soup.find_all("div", string=lambda text: text and "Mid" in text)
            
            assert len(elements) > 0, "Элемент с текстом 'Mid' не найден"

    def test_offlane_position_xpath(self):
        """Тест XPath для позиции Offlane"""
        xpath = "//div[contains(text(), 'Off')]"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            
            soup = BeautifulSoup(page_source, "html.parser")
            elements = soup.find_all("div", string=lambda text: text and "Off" in text)
            
            assert len(elements) > 0, "Элемент с текстом 'Off' не найден"

    def test_pos4_position_xpath(self):
        """Тест XPath для позиции Pos 4"""
        xpath = "//div[contains(text(), 'Pos 4')]"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            
            soup = BeautifulSoup(page_source, "html.parser")
            elements = soup.find_all("div", string=lambda text: text and "Pos 4" in text)
            
            assert len(elements) > 0, "Элемент с текстом 'Pos 4' не найден"

    def test_pos5_position_xpath(self):
        """Тест XPath для позиции Pos 5"""
        xpath = "//div[contains(text(), 'Pos 5')]"
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            page_source = manager.get_page_source()
            
            soup = BeautifulSoup(page_source, "html.parser")
            elements = soup.find_all("div", string=lambda text: text and "Pos 5" in text)
            
            assert len(elements) > 0, "Элемент с текстом 'Pos 5' не найден"

    def test_all_positions_clickable(self):
        """Тест что все позиции кликабельны"""
        positions_xpaths = {
            "Carry": "//div[contains(text(), 'Carry')]",
            "Mid": "//div[contains(text(), 'Mid')]",
            "Offlane": "//div[contains(text(), 'Off')]",
            "Pos 4": "//div[contains(text(), 'Pos 4')]",
            "Pos 5": "//div[contains(text(), 'Pos 5')]",
        }
        
        with ScrapingManager(headless=True) as manager:
            manager.navigate_to_page("https://dota2protracker.com/meta")
            
            failed_positions = []
            for pos_name, xpath in positions_xpaths.items():
                result = manager.click_element_safely(xpath, timeout=15)
                if not result:
                    failed_positions.append(pos_name)
            
            assert len(failed_positions) == 0, f"Не удалось кликнуть по позициям: {failed_positions}"
