"""
Парсинг страницы D2PT meta для pos 4: вывод списка герой — фасет по порядку.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dota2_data_scraper.modules.core.scraping_manager import ScrapingManager
from dota2_data_scraper.modules.scrapers.hero_scraper import HeroScraper


def main():
    url = "https://dota2protracker.com/meta?mmr=7000&position=pos%2B4&period=8"
    with ScrapingManager(headless=True) as manager:
        manager.navigate_to_page(url)
        time.sleep(3)
        scraper = HeroScraper()
        df = scraper._extract_table_data(manager.driver)
        if df.empty:
            print("Таблица не найдена или пуста.")
            return 1
        df = scraper._ensure_facet_names_and_numbers(df)
        if "Hero" not in df.columns or "Facet" not in df.columns:
            print("Колонки Hero/Facet не найдены:", list(df.columns))
            return 1
        def facet_short(s):
            if not s or not isinstance(s, str):
                return ""
            t = s.split("\n")[0].strip()
            markers = (
                "This facet", " doesn't ", "For the ", "When the ", "When ",
                "While ", "Gains ", "Deals ", "Grants ", "Units ", "Upon ",
                "Increases ", "Additionally ", "Also ", " applies ", " can ",
                " grants ", " restores ", " steals ", " deals ", " has ",
                " have ", " form ", " is ", " are ", " was ", " were ",
                "Summons ", "Grants ", "Increases ", "When ", "If the ",
                "Shuriken ", "Wex ", "Wex gains", "Quas ", "Exort ", "Nether ", "Cold ",
                "Charge of ", "Charge of Darkness",
                "Death Ward ", "Mana Drain ", "Sun Ray ", "Chain ", "Soul ",
                "Thunder ", "Natural Order ", "Disseminate ", "Ink Swell ",
                "Aftershock ", "Sticky Napalm ", "Starstorm", "Rot ",
                "Sharpshooter ", "Shockwave ", "Finger of Death ", "Cooldowns ",
                "Shackleshot ", "Firefly ", "Rebound ", "Blast Off", "Scatterblast ",
                "Tossed ", "Shrapnel ", "Casting ", "Stolen ", "Powershot ",
            )
            t_lower = t.lower()
            for marker in markers:
                pos = t_lower.find(marker.lower())
                if pos > 2:
                    t = t[:pos].strip()
                    t_lower = t.lower()
            if len(t) > 45:
                t = t[:45].rsplit(" ", 1)[0] if " " in t[:45] else t[:45]
            return t or s[:35]
        n = 0
        for _, row in df.iterrows():
            hero = row.get("Hero") or ""
            facet = facet_short(row.get("Facet"))
            if not hero or hero == "None":
                continue
            n += 1
            print(f"{n}. {hero} — {facet}")
        print(f"\nВсего: {len(df)} записей")
    return 0


if __name__ == "__main__":
    sys.exit(main())
