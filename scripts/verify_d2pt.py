"""
Проверка работы скрапера только для главной страницы d2pt (dota2protracker.com/meta).
Dotabuff не используется.
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bs4 import BeautifulSoup

from dota2_data_scraper.modules.core.scraping_manager import ScrapingManager
from dota2_data_scraper.modules.scrapers.hero_scraper import HeroScraper
from selenium.webdriver.common.by import By


def _norm_int(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    s = str(v).strip()
    if not s or s == "-":
        return None
    digits = "".join(ch for ch in s if ch.isdigit())
    return int(digits) if digits else None


def _norm_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("%", "")
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _pick_col(headers, variants):
    lowered = [(h or "").strip().lower() for h in headers]
    for i, h in enumerate(lowered):
        for v in variants:
            if v in h:
                return i
    return -1


def _dom_table_snapshot(driver, max_rows=15):
    try:
        thead = driver.find_element(By.XPATH, "//div[contains(@class,'thead')]")
    except Exception:
        thead = None

    headers = []
    if thead is not None:
        for col in thead.find_elements(By.XPATH, "./div"):
            try:
                btns = col.find_elements(By.TAG_NAME, "button")
                txt = (btns[0].text if btns else col.text).strip()
            except Exception:
                txt = ""
            headers.append(txt or None)

    row_els = []
    try:
        tbody = driver.find_element(By.XPATH, "//div[contains(@class,'tbody')]")
        row_els = tbody.find_elements(
            By.XPATH, "./div[contains(@class,'grid') and contains(@class,'grid-cols-14')]"
        )
    except Exception:
        row_els = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'grid') and contains(@class,'grid-cols-14') and @style]",
        )

    rows = []
    for row_el in row_els[:max_rows]:
        cells = row_el.find_elements(By.XPATH, "./div")
        hero_alt = None
        try:
            imgs = cells[0].find_elements(By.TAG_NAME, "img") if cells else []
            if imgs:
                hero_alt = (imgs[0].get_attribute("alt") or "").strip() or None
        except Exception:
            hero_alt = None

        values = []
        for c in cells:
            try:
                values.append((c.text or "").strip() or None)
            except Exception:
                values.append(None)
        rows.append({"_hero": hero_alt, "_values": values})

    return headers, rows


def _compare_position(manager, scraper, role, xpath, sample_rows=12):
    if not manager.click_element_safely(xpath, timeout=15):
        print(f"[FAIL] Не удалось кликнуть по кнопке позиции: {role}")
        return False

    time.sleep(1.0)

    dom_headers, dom_rows = _dom_table_snapshot(manager.driver, max_rows=sample_rows)
    df = scraper._extract_table_data(manager.driver)
    if df.empty or "Hero" not in df.columns:
        print(f"[FAIL] Позиция {role}: парсер вернул пустые данные")
        return False

    df["Role"] = role

    df_headers = list(df.columns)
    df_match_col = next((c for c in df_headers if "match" in str(c).lower()), None)
    df_wr_col = next((c for c in df_headers if str(c).strip().lower() == "wr" or "win" in str(c).lower()), None)
    df_d2pt_col = next((c for c in df_headers if "d2pt" in str(c).lower() or "rating" in str(c).lower()), None)

    dom_match_idx = _pick_col(dom_headers, ["match"])
    dom_wr_idx = _pick_col(dom_headers, ["wr", "win"])
    dom_d2pt_idx = _pick_col(dom_headers, ["d2pt", "rating"])

    if not df_match_col or not df_wr_col or not df_d2pt_col:
        print(f"[FAIL] Позиция {role}: не нашёл колонки Matches/WR/D2PT в DataFrame: {df_headers}")
        return False
    if dom_match_idx == -1 or dom_wr_idx == -1 or dom_d2pt_idx == -1:
        print(f"[FAIL] Позиция {role}: не нашёл колонки Matches/WR/D2PT в DOM заголовках: {dom_headers}")
        return False

    mismatches = 0
    checked = 0
    n = min(len(dom_rows), len(df))
    for i in range(n):
        r = dom_rows[i]
        values = r.get("_values") or []
        if max(dom_match_idx, dom_wr_idx, dom_d2pt_idx) >= len(values):
            continue

        dom_matches = _norm_int(values[dom_match_idx])
        dom_wr = _norm_float(values[dom_wr_idx])
        dom_d2pt = _norm_float(values[dom_d2pt_idx])

        df_row = df.iloc[i]
        df_matches = _norm_int(df_row.get(df_match_col))
        df_wr = _norm_float(df_row.get(df_wr_col))
        df_d2pt = _norm_float(df_row.get(df_d2pt_col))

        ok = True
        if dom_matches is not None and df_matches is not None and dom_matches != df_matches:
            ok = False
        if dom_wr is not None and df_wr is not None and abs(dom_wr - df_wr) > 0.11:
            ok = False
        if dom_d2pt is not None and df_d2pt is not None and abs(dom_d2pt - df_d2pt) > 0.11:
            ok = False

        hero = r.get("_hero") or "?"
        checked += 1
        if not ok:
            mismatches += 1
            print(
                f"[MISMATCH] {role} row {i} ({hero}): "
                f"DOM(matches={dom_matches}, wr={dom_wr}, d2pt={dom_d2pt}) "
                f"!= DF(matches={df_matches}, wr={df_wr}, d2pt={df_d2pt})"
            )

    if checked == 0:
        print(f"[FAIL] Позиция {role}: не удалось проверить строки (DOM snapshot пуст)")
        return False

    if mismatches:
        print(f"[FAIL] Позиция {role}: расхождений {mismatches} из {checked} (первые {sample_rows} строк)")
        return False

    print(f"[OK] Позиция {role}: совпало {checked} из {checked} (первые {sample_rows} строк)")
    return True


def verify_d2pt(sample_rows=12):
    url = "https://dota2protracker.com/meta"
    with ScrapingManager(headless=True) as manager:
        manager.navigate_to_page(url)
        page_source = manager.get_page_source()

        if len(page_source) == 0:
            print("[FAIL] Страница не загрузилась")
            return False
        if "dota2protracker" not in page_source.lower():
            print("[FAIL] Неверная страница (нет dota2protracker)")
            return False
        print("[OK] Страница загружена")

        soup = BeautifulSoup(page_source, "html.parser")
        has_grid = lambda c: c and "grid" in (c if isinstance(c, str) else c)
        table_rows = soup.find_all("div", class_=has_grid, style=True)
        if not table_rows:
            table_rows = soup.find_all("div", class_=lambda c: c and "grid" in c and "grid-cols-14" in c)
        if len(table_rows) == 0:
            print("[FAIL] Нет строк таблицы (grid)")
            return False
        print("[OK] Найдены строки таблицы")

        scraper = HeroScraper(headless=True)
        scraper.facet_parser.hero_facets_cache = {}

        positions = [
            ("pos 1", "//button[.//img[@alt='Carry']]"),
            ("pos 2", "//button[.//img[@alt='Mid']]"),
            ("pos 3", "//button[.//img[@alt='Off']]"),
            ("pos 4", "//button[.//img[@alt='Pos 4']]"),
            ("pos 5", "//button[.//img[@alt='Pos 5']]"),
        ]

        ok = True
        for role, xpath in positions:
            if not _compare_position(manager, scraper, role, xpath, sample_rows=sample_rows):
                ok = False

        return ok


if __name__ == "__main__":
    try:
        success = verify_d2pt(sample_rows=12)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
