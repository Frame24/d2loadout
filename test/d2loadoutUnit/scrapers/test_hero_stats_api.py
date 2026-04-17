"""Тесты сбора статистики через D2PT API (без сети при моке)."""

from unittest.mock import patch

import pandas as pd

from dota2_data_scraper.modules.scrapers.hero_stats_api import (
    _row_from_entry,
    fetch_heroes_stats_dataframe,
)


def test_row_from_entry_wr_and_d2pt():
    row = _row_from_entry(
        {
            "hero_name": "Anti-Mage",
            "hero_id": 1,
            "position": "pos 5",
            "matches": 10,
            "wins": 4,
            "d2pt_rating": 123,
        }
    )
    assert row["Hero"] == "Anti-Mage"
    assert row["hero_id"] == 1
    assert row["Role"] == "pos 5"
    assert row["Matches"] == 10
    assert row["WR"] == 40.0
    assert row["D2PT Rating"] == 123.0
    assert row["Facet"] == "No Facet"


def test_row_from_entry_zero_matches():
    row = _row_from_entry(
        {
            "hero_name": "X",
            "hero_id": 99,
            "position": "pos 1",
            "matches": 0,
            "wins": 0,
            "d2pt_rating": 0,
        }
    )
    assert pd.isna(row["WR"])
    assert row["hero_id"] == 99


@patch("dota2_data_scraper.modules.scrapers.hero_stats_api._warm_d2pt_session")
@patch("dota2_data_scraper.modules.scrapers.hero_stats_api._fetch_position_json")
def test_fetch_heroes_stats_dataframe_concat_five_positions(
    mock_fetch, _mock_warm_session
):
    def _one_hero(position_label: str, _opener, **_kwargs):
        return [
            {
                "hero_name": "Slark",
                "hero_id": 93,
                "position": position_label,
                "matches": 100,
                "wins": 53,
                "d2pt_rating": 3000,
            }
        ]

    mock_fetch.side_effect = _one_hero
    df = fetch_heroes_stats_dataframe()
    assert mock_fetch.call_count == 5
    assert len(df) == 5
    assert set(df["Role"].unique()) == {
        "pos 1",
        "pos 2",
        "pos 3",
        "pos 4",
        "pos 5",
    }
    assert df["WR"].iloc[0] == 53.0
    assert "D2PT Rating" in df.columns
    assert (df["hero_id"] == 93).all()
