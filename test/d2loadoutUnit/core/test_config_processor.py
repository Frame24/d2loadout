"""
Модульные тесты для ConfigProcessor
"""

import pytest
import pandas as pd
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from dota2_data_scraper.modules.core.config_processor import ConfigProcessor


class TestConfigProcessor:
    """Тесты для ConfigProcessor - границы модуля"""

    @pytest.fixture
    def temp_dir(self):
        """Временная директория для тестов"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def sample_heroes_df(self):
        """Тестовый DataFrame с данными героев"""
        return pd.DataFrame({
            "Hero": ["Juggernaut", "Pudge", "Invoker"],
            "Role": ["pos 1", "pos 4", "pos 2"],
            "Matches": [1000, 500, 800],
            "WR": [52.5, 48.3, 55.1],
            "D2PT Rating": [7.5, 6.2, 8.1],
            "Facet": ["Facet 1", "Facet 2", "Facet 1"]
        })

    @pytest.fixture
    def processor(self, temp_dir):
        """Экземпляр ConfigProcessor с моками"""
        with patch("dota2_data_scraper.modules.core.config_processor.DataManager") as mock_dm:
            mock_dm_instance = Mock()
            mock_dm_instance.output_dir = temp_dir
            mock_dm.return_value = mock_dm_instance
            
            with patch("dota2_data_scraper.modules.core.config_processor.SteamManager"):
                processor = ConfigProcessor()
                processor.data_manager = mock_dm_instance
                yield processor

    @patch("dota2_data_scraper.modules.core.config_processor.requests.get")
    def test_load_heroes_from_api_success(self, mock_get, processor):
        """Тест успешной загрузки героев из API"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"displayName": "Juggernaut", "hero_id": 8},
            {"displayName": "Pudge", "hero_id": 14}
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mapping = processor._load_heroes_from_api()
        assert "Juggernaut" in mapping
        assert mapping["Juggernaut"] == 8
        assert mapping["Pudge"] == 14

    @patch("dota2_data_scraper.modules.core.config_processor.requests.get")
    def test_load_heroes_from_api_fallback(self, mock_get, processor):
        """Тест использования fallback маппинга при ошибке API"""
        mock_get.side_effect = Exception("API недоступен")
        mapping = processor._get_fallback_mapping()
        assert "Anti-Mage" in mapping
        assert mapping["Anti-Mage"] == 1
        assert mapping["Juggernaut"] == 8

    def test_map_hero_names_to_ids(self, processor, sample_heroes_df):
        """Тест маппинга имен героев к ID"""
        with patch.object(processor, "_load_heroes_from_api") as mock_load:
            mock_load.return_value = {
                "Juggernaut": 8,
                "Pudge": 14,
                "Invoker": 74
            }
            mapped_ids = processor._map_hero_names_to_ids(sample_heroes_df["Hero"])
            assert mapped_ids.iloc[0] == 8
            assert mapped_ids.iloc[1] == 14
            assert mapped_ids.iloc[2] == 74

    def test_save_config_success(self, processor, temp_dir):
        """Тест успешного сохранения конфигурации"""
        import json
        config = {
            "version": 3,
            "configs": [
                {
                    "config_name": "Test Config",
                    "categories": []
                }
            ]
        }
        # Мокаем os.makedirs и os.path.join
        with patch("dota2_data_scraper.modules.core.config_processor.os.makedirs"):
            with patch("dota2_data_scraper.modules.core.config_processor.os.path.join") as mock_join:
                test_path = os.path.join(temp_dir, "hero_configs.json")
                mock_join.return_value = test_path
                with patch("builtins.open", create=True) as mock_open:
                    mock_file = Mock()
                    mock_file.write = Mock()
                    mock_open.return_value.__enter__.return_value = mock_file
                    result = processor._save_config(config)
                    assert result is True
                    assert mock_open.called

    def test_create_facet_config_with_data(self, processor, sample_heroes_df):
        """Тест создания конфигурации фасетов с данными"""
        sample_heroes_df["facet_number"] = [1, 2, 1]
        sample_heroes_df["hero_id"] = [8, 14, 74]
        sample_heroes_df["D2PT Rating"] = [7.5, 6.2, 8.1]
        
        config = processor._create_facet_config(
            sample_heroes_df,
            "Test Config",
            "WR",
            min_matches=100,
            wr_threshold=50
        )
        assert config is not None
        assert config["config_name"] == "Test Config"
        assert "categories" in config

    def test_create_facet_config_empty_data(self, processor):
        """Тест создания конфигурации с пустыми данными"""
        empty_df = pd.DataFrame()
        config = processor._create_facet_config(
            empty_df,
            "Test Config",
            "WR",
            min_matches=100
        )
        assert config is None

    def test_create_facet_config_no_facet_number(self, processor, sample_heroes_df):
        """Тест создания конфигурации без поля facet_number"""
        config = processor._create_facet_config(
            sample_heroes_df,
            "Test Config",
            "WR",
            min_matches=100
        )
        assert config is None
