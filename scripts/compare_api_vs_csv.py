import os
import sys
import hashlib

import pandas as pd

base_dir = os.path.dirname(os.path.dirname(__file__))
pkg_dir = os.path.join(base_dir, "dota2_data_scraper")
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from modules.scrapers.hero_stats_api import fetch_heroes_stats_dataframe


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cols = [
        c
        for c in ["Hero", "hero_id", "Role", "Matches", "WR", "D2PT Rating", "Facet"]
        if c in df.columns
    ]
    df = df[cols]

    if "hero_id" in df.columns:
        df["hero_id"] = pd.to_numeric(df["hero_id"], errors="coerce").fillna(0).astype(int)
    if "Matches" in df.columns:
        df["Matches"] = (
            pd.to_numeric(df["Matches"], errors="coerce").fillna(0).astype(int)
        )
    if "WR" in df.columns:
        df["WR"] = pd.to_numeric(df["WR"], errors="coerce").round(10)
    if "D2PT Rating" in df.columns:
        df["D2PT Rating"] = pd.to_numeric(df["D2PT Rating"], errors="coerce").round(10)
    for c in ["Hero", "Role", "Facet"]:
        if c in df.columns:
            df[c] = df[c].astype(str).fillna("")

    sort = [c for c in ["Role", "Hero", "hero_id"] if c in df.columns]
    df = df.sort_values(sort).reset_index(drop=True)
    return df


def _digest(df: pd.DataFrame) -> str:
    b = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    df_api = fetch_heroes_stats_dataframe()
    df_csv = pd.read_csv("configs/heroes_data.csv")

    n_api = _norm(df_api)
    n_csv = _norm(df_csv)

    ha = _digest(n_api)
    hc = _digest(n_csv)

    print(f"API rows={len(n_api)} sha256={ha}")
    print(f"CSV rows={len(n_csv)} sha256={hc}")
    print(f"MATCH={ha == hc}")

    if ha != hc:
        key = ["Hero", "Role", "hero_id"]
        merged = n_api.merge(n_csv, on=key, how="outer", indicator=True)
        print(merged["_merge"].value_counts().to_string())
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

