"""
Модульные тесты для FacetAPIParser
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from dota2_data_scraper.modules.utils.facet_api_parser import FacetAPIParser


class TestFacetAPIParser:
    """Тесты для FacetAPIParser - границы модуля"""

    @pytest.fixture
    def parser(self):
        """Экземпляр FacetAPIParser"""
        return FacetAPIParser()

    def test_parser_initialization(self, parser):
        """Тест инициализации парсера"""
        assert parser.hero_facets_cache == {}

    def test_extract_repo_js_url_from_html(self, parser):
        """Тест извлечения URL repo-*.js из HTML"""
        html = '<script src="/static/repo-abc123.js"></script>'
        url = parser._extract_repo_js_url_from_html(html)
        assert url == "https://www.dotabuff.com/static/repo-abc123.js"

    def test_extract_facets_from_repo(self, parser):
        """Тест извлечения фасетов из JS"""
        js_text = 'const f = JSON.parse(`[{"hero_id": 8, "name": "Facet 1", "hero_variant": 1, "id": 1}]`)'
        facets = parser._extract_facets_from_repo(js_text)
        assert len(facets) > 0
        assert facets[0]["hero_id"] == 8

    def test_build_mapping_from_facets(self, parser):
        """Тест построения маппинга из фасетов"""
        facets = [
            {"hero_id": 8, "name": "Facet 1", "hero_variant": 1, "id": 1, "slug": "juggernaut-1-test"},
            {"hero_id": 8, "name": "Facet 2", "hero_variant": 2, "id": 2, "slug": "juggernaut-2-test"}
        ]
        mapping = parser._build_mapping_from_facets(facets)
        assert "Juggernaut" in mapping
        assert "Facet 1" in mapping["Juggernaut"]
        assert mapping["Juggernaut"]["Facet 1"] == 1

    def test_name_from_slug(self, parser):
        """Тест извлечения имени героя из slug"""
        assert parser._name_from_slug("juggernaut-1-test") == "Juggernaut"
        assert parser._name_from_slug("anti-mage-1-test") == "Anti-Mage"
        assert parser._name_from_slug("natures-prophet-1-test") == "Nature's Prophet"

    def test_alias_from_description(self, parser):
        """Тест извлечения алиаса из описания"""
        desc = "Grants bonus attack speed and movement speed"
        alias = parser._alias_from_description(desc)
        assert alias is not None
        assert isinstance(alias, str)

    def test_get_name_to_order_for_hero(self, parser):
        """Тест получения маппинга для конкретного героя"""
        parser.hero_facets_cache = {
            "Juggernaut": {"Facet 1": 1, "Facet 2": 2}
        }
        mapping = parser.get_name_to_order_for_hero("Juggernaut")
        assert mapping["Facet 1"] == 1
        assert mapping["Facet 2"] == 2

    def test_get_facet_number_for_hero(self, parser):
        """Тест получения номера фасета для героя"""
        parser.hero_facets_cache = {
            "Juggernaut": {"Facet 1": 1, "Facet 2": 2}
        }
        number = parser.get_facet_number_for_hero("Juggernaut", "Facet 1")
        assert number == 1

    @patch("dota2_data_scraper.modules.utils.facet_api_parser.requests.get")
    def test_fetch_url_success(self, mock_get, parser):
        """Тест успешного получения URL"""
        mock_response = Mock()
        mock_response.text = "<html>test</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = parser._fetch_url("https://example.com")
        assert result == "<html>test</html>"
        mock_get.assert_called_once()
