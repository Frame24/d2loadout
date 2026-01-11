"""
Модульные тесты для DataManager
"""

import pytest
import pandas as pd
import os
import tempfile
import shutil
from dota2_data_scraper.modules.core.data_manager import DataManager


class TestDataManager:
    """Тесты для DataManager - границы модуля"""

    @pytest.fixture
    def temp_dir(self):
        """Временная директория для тестов"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def data_manager(self, temp_dir):
        """Экземпляр DataManager с временной директорией"""
        return DataManager(output_dir=temp_dir)

    @pytest.fixture
    def sample_dataframe(self):
        """Тестовый DataFrame"""
        return pd.DataFrame({
            "Hero": ["Juggernaut", "Pudge", "Invoker"],
            "Role": ["pos 1", "pos 4", "pos 2"],
            "Matches": [1000, 500, 800],
            "WR": [52.5, 48.3, 55.1]
        })

    def test_save_dataframe_success(self, data_manager, sample_dataframe, temp_dir):
        """Тест успешного сохранения DataFrame"""
        result = data_manager.save_dataframe(sample_dataframe, "test_data.csv")
        assert result is True
        filepath = os.path.join(temp_dir, "test_data.csv")
        assert os.path.exists(filepath)

    def test_save_dataframe_file_exists(self, data_manager, sample_dataframe, temp_dir):
        """Тест что файл создается и содержит данные"""
        data_manager.save_dataframe(sample_dataframe, "test_data.csv")
        filepath = os.path.join(temp_dir, "test_data.csv")
        loaded_df = pd.read_csv(filepath)
        assert len(loaded_df) == 3
        assert "Hero" in loaded_df.columns

    def test_load_dataframe_success(self, data_manager, sample_dataframe):
        """Тест успешной загрузки DataFrame"""
        data_manager.save_dataframe(sample_dataframe, "test_data.csv")
        loaded_df = data_manager.load_dataframe("test_data.csv")
        assert loaded_df is not None
        assert len(loaded_df) == 3
        assert list(loaded_df.columns) == list(sample_dataframe.columns)

    def test_load_dataframe_not_found(self, data_manager):
        """Тест загрузки несуществующего файла"""
        result = data_manager.load_dataframe("nonexistent.csv")
        assert result is None

    def test_merge_heroes_and_facets(self, data_manager):
        """Тест объединения данных героев и фасетов"""
        heroes_df = pd.DataFrame({
            "Hero": ["Juggernaut", "Pudge"],
            "hero_id": [8, 14]
        })
        facets_df = pd.DataFrame({
            "Hero": ["Juggernaut", "Pudge"],
            "Facet": ["Facet 1", "Facet 2"],
            "Matches": [1000, 500],
            "Win Rate": [52.5, 48.3],
            "Role": ["pos 1", "pos 4"]
        })
        merged = data_manager.merge_heroes_and_facets(heroes_df, facets_df)
        assert not merged.empty
        assert "hero_id" in merged.columns
        assert "Facet" in merged.columns
        assert "Role" in merged.columns

    def test_get_file_info_exists(self, data_manager, sample_dataframe):
        """Тест получения информации о существующем файле"""
        data_manager.save_dataframe(sample_dataframe, "test_data.csv")
        info = data_manager.get_file_info("test_data.csv")
        assert info["exists"] is True
        assert "size" in info
        assert "path" in info

    def test_get_file_info_not_exists(self, data_manager):
        """Тест получения информации о несуществующем файле"""
        info = data_manager.get_file_info("nonexistent.csv")
        assert info["exists"] is False

    def test_list_data_files(self, data_manager, sample_dataframe):
        """Тест получения списка CSV файлов"""
        data_manager.save_dataframe(sample_dataframe, "test1.csv")
        data_manager.save_dataframe(sample_dataframe, "test2.csv")
        files = data_manager.list_data_files()
        assert "test1.csv" in files
        assert "test2.csv" in files
