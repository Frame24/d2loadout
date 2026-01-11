"""
Модульные тесты для HeroScraper
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from dota2_data_scraper.modules.scrapers.hero_scraper import HeroScraper


class TestHeroScraper:
    """Тесты для HeroScraper - границы модуля"""

    @pytest.fixture
    def scraper(self):
        """Экземпляр HeroScraper"""
        return HeroScraper(headless=True)

    def test_scraper_initialization(self, scraper):
        """Тест инициализации скрапера"""
        assert scraper.headless is True
        assert scraper.positions is not None
        assert len(scraper.positions) == 5

    def test_role_mapping(self, scraper):
        """Тест маппинга ролей"""
        assert scraper.role_mapping["Carry (pos 1)"] == "pos 1"
        assert scraper.role_mapping["Mid (pos 2)"] == "pos 2"
        assert scraper.role_mapping["Offlaner (pos 3)"] == "pos 3"

    @patch("dota2_data_scraper.modules.scrapers.hero_scraper.ScrapingManager")
    def test_scrape_heroes_data_structure(self, mock_manager_class, scraper):
        """Тест структуры данных при скрапинге"""
        mock_manager = MagicMock()
        mock_manager_class.return_value.__enter__.return_value = mock_manager
        
        mock_driver = MagicMock()
        mock_manager.driver = mock_driver
        mock_manager.click_element_safely.return_value = True
        
        mock_driver.page_source = """
        <html>
        <div class="grid" style="display: grid;">
            <div>Hero</div><div>Matches</div><div>WR</div>
        </div>
        <div class="grid" style="display: grid;">
            <div><img alt="Juggernaut"/></div><div>1000</div><div>52.5%</div>
        </div>
        </html>
        """
        
        with patch.object(scraper, "_extract_table_data") as mock_extract:
            mock_extract.return_value = pd.DataFrame({
                "Hero": ["Juggernaut"],
                "Matches": [1000],
                "WR": [52.5],
                "Role": ["pos 1"]
            })
            
            with patch.object(scraper, "_ensure_facet_names_and_numbers") as mock_ensure:
                mock_ensure.return_value = pd.DataFrame({
                    "Hero": ["Juggernaut"],
                    "Facet": ["Facet 1"],
                    "Matches": [1000],
                    "WR": [52.5],
                    "Role": ["pos 1"]
                })
                
                result = scraper.scrape_heroes_data()
                assert isinstance(result, pd.DataFrame)
                assert not result.empty

    def test_ensure_facet_names_and_numbers_structure(self, scraper):
        """Тест структуры данных после обработки фасетов"""
        df = pd.DataFrame({
            "Hero": ["Juggernaut", "Pudge"],
            "Role": ["pos 1", "pos 4"],
            "Facet": ["Facet 1", "Facet 2"]
        })
        
        with patch.object(scraper.facet_parser, "get_hero_facets_mapping") as mock_mapping:
            mock_mapping.return_value = {
                "Juggernaut": {"Facet 1": 1},
                "Pudge": {"Facet 2": 2}
            }
            
            result = scraper._ensure_facet_names_and_numbers(df)
            assert "Facet" in result.columns
            assert "facet_number" in result.columns

    def test_clean_data_percentage(self, scraper):
        """Тест очистки данных с процентами"""
        df = pd.DataFrame({
            "WR": ["52.5%", "48.3%", "55.1%"]
        })
        cleaned = scraper._clean_data(df)
        # Проверяем что значения стали числовыми (pandas может использовать Float64)
        assert pd.api.types.is_numeric_dtype(cleaned["WR"]), f"Ожидался числовой тип, получено: {cleaned['WR'].dtype}"

    def test_clean_data_range(self, scraper):
        """Тест очистки данных с диапазонами"""
        df = pd.DataFrame({
            "Matches": ["1000 (500-1500)"]
        })
        cleaned = scraper._clean_data(df)
        assert cleaned["Matches"].dtype == object
