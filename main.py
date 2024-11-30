## Preparations
import warnings
warnings.filterwarnings("ignore")
print("d2loadout update started")
import json
import os
import re
import pandas as pd
import requests
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import ast
import html_to_json
chrome_options = webdriver.ChromeOptions()

chrome_options.add_argument("user-agent=" + UserAgent().random)
chrome_options.add_argument("--disable-blink-features")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--incognito")
chrome_options.add_argument("disable-infobars")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("detach", True)

chrome_options.add_argument('headless')
chrome_options.add_argument('window-size=1920x1080')
chrome_options.add_argument("disable-gpu")

chrome_options.page_load_strategy = 'eager'


os.environ["PATH"] += r"C:\Program Files (x86)\Chromedriver.exe"
driver = webdriver.Chrome(options=chrome_options)
## Meta
link_meta = "https://dota2protracker.com/meta"
driver.implicitly_wait(3)
driver.get(link_meta)
driver.implicitly_wait(10)
def get_d2pt_page_table(driver):
    # finding table rows in site and converting to format, readable by pandas
    time.sleep(0.2)
    category_name_elements = driver.find_elements(By.XPATH, "//*[@data-wr]")
    div_inner_strs = []
    for elem in category_name_elements:
        div_inner_str = (
            elem.get_attribute("outerHTML").split(">")[0].replace("data-", "")
        )
        div_items = re.findall(
            r'[-\w]+="[\w\d\s.,\/#!$%\^&\*;:{}=\-_`~()\'\\/\[\]]+"', div_inner_str
        )
        temp_dict = {}
        for item in div_items:
            temp_split = item.split("=")
            temp_dict[temp_split[0]] = temp_split[1].replace('"', "")
        div_inner_strs.append(temp_dict)

    # Dataframe dtype converts
    df_heroes_table = pd.DataFrame(data=div_inner_strs)
    df_heroes_table = df_heroes_table.apply(pd.to_numeric, errors="ignore")
    df_heroes_table = df_heroes_table.round(1)
    return df_heroes_table
print("checking meta...")
print("fetching heroes info for pos 1")
driver.find_element(By.XPATH, "//div[contains(text(), 'Carry')]").click()
df_1 = get_d2pt_page_table(driver)

print("fetching heroes info for pos 2")
driver.find_element(By.XPATH, "//div[contains(text(), 'Mid')]").click()
df_2 = get_d2pt_page_table(driver)

print("fetching heroes info for pos 3")
driver.find_element(By.XPATH, "//div[contains(text(), 'Off')]").click()
df_3 = get_d2pt_page_table(driver)

print("fetching heroes info for pos 4")
driver.find_element(By.XPATH, "//div[contains(text(), 'Pos 4')]").click()
df_4 = get_d2pt_page_table(driver)

print("fetching heroes info for pos 5")
driver.find_element(By.XPATH, "//div[contains(text(), 'Pos 5')]").click()
df_5 = get_d2pt_page_table(driver)

df_full = pd.concat([df_1, df_2, df_3, df_4, df_5], axis=0)
# df_full = df_full.drop(["class"], axis=1)
df_full
## Facets
link = "https://dota2protracker.com/facets"
driver.implicitly_wait(2)
driver.get(link)
hero_req = requests.get("https://dota2protracker.com/hero/Tiny")
facetData = re.findall(r'facetData:{.+}', hero_req.text)[0].replace("facetData:", "")
import js2py
tojs = re.findall(r'const data = \[.+\"data\":{', hero_req.text)[0]
tojs = tojs + re.findall(r'facetData:{.+},buildData', hero_req.text)[0].replace(",buildData", "}}]")
js_res = js2py.eval_js(tojs) 
d = js_res[2]["data"]["facetData"]
[d[item]["facets"] for item in d]
facets_d = {}
for item in d:
    facet_names = []
    for facets in d[item]["facets"]:
        facet_names.append(facets["name"].upper())
    facets_d[item] = facet_names
facets_d
# with open("./facetData.json", 'w+', encoding="utf-8") as f:
#     f.write(re.findall(r'facetData:{.+}', hero_req.text)[0].replace("facetData:", ""))
def get_d2pt_page_table_facets(driver):
    time.sleep(0.2)
    # finding table rows in site and converting to format, readable by pandas
    category_name_elements = driver.find_elements(
        By.CSS_SELECTOR, ".flex.bg-d2pt-gray-3.gap-1"
    )
    category_name_elements += driver.find_elements(
        By.CSS_SELECTOR, ".flex.bg-d2pt-gray-4.gap-1"
    )
    hero_rows = [item.text.split("\n") for item in category_name_elements]
    hero_columns = [item for item in driver.find_element(
        By.CSS_SELECTOR, ".flex.gap-1.font-medium.text-sm.mb-1"
    ).text.split("\n") if item != "Trend"]
        
    # Dataframe dtype converts
    df_heroes_table = pd.DataFrame(data=hero_rows, columns=hero_columns)
    df_heroes_table = df_heroes_table.apply(pd.to_numeric, errors='ignore')
    df_heroes_table = df_heroes_table.round(1)
    return df_heroes_table
print("checking facets...")
print("fetching facets info for pos 1")
driver.find_element(By.XPATH, "//div[contains(text(), 'Carry')]").click()
df_1 = get_d2pt_page_table_facets(driver)
df_1["pos"] = "pos 1"

print("fetching facets info for pos 2")
driver.find_element(By.XPATH, "//div[contains(text(), 'Mid')]").click()
df_2 = get_d2pt_page_table_facets(driver)
df_2["pos"] = "pos 2"

print("fetching facets info for pos 3")
driver.find_element(By.XPATH, "//div[contains(text(), 'Off')]").click()
df_3 = get_d2pt_page_table_facets(driver)
df_3["pos"] = "pos 3"

print("fetching facets info for pos 4")
driver.find_element(By.XPATH, "//div[contains(text(), 'Pos 4')]").click()
df_4 = get_d2pt_page_table_facets(driver)
df_4["pos"] = "pos 4"

print("fetching facets info for pos 5")
driver.find_element(By.XPATH, "//div[contains(text(), 'Pos 5')]").click()
df_5 = get_d2pt_page_table_facets(driver)
df_5["pos"] = "pos 5"

df_full_facets = pd.concat([df_1,df_2,df_3,df_4,df_5], axis=0)

df_full_facets = df_full_facets.rename({
    "Hero": "hero",
    "Facet": "facet",
    "Matches": "matches",
    "Win Rate": "wr"
}, axis=1)[["hero", "facet", "matches", "wr", "pos"]]

df_full_facets["wr"] = df_full_facets["wr"].apply(lambda x: x.replace("%", ""))
df_full_facets = df_full_facets.apply(pd.to_numeric, errors='ignore')

df_full_facets
## Results
print("creating in-game loadouts")
req = requests.get("https://dota2protracker.com/_get/search").json()
hero_names = [item["displayName"] for item in req["heroes"]]
hero_ids = [item["hero_id"] for item in req["heroes"]]
hero_id = dict(zip(hero_names, hero_ids))
df_full["hero_id"] = df_full["hero"].apply(lambda x: hero_id[x])
df_full_facets["hero_id"] = df_full_facets["hero"].apply(lambda x: hero_id[x])
df_full_facets["facet_id"] = df_full_facets.apply(lambda x: facets_d[f"{x.hero_id}"].index(x.facet), axis=1)
pd.set_option('display.max_rows', 20)
df_full_facets
pd.set_option('display.max_rows', 20)
def make_config(get_df_func, df, name):
    margin = 20
    width = 585 - margin
    height = 189 - margin
    not_included = [
        id
        for id in hero_ids
        if id
        not in [
            j for sub in [get_df_func(df, i) for i in [1, 2, 3, 4, 5]] for j in sub
        ]
    ]

    return {
        "config_name": name,
        "categories": [
            {
                "category_name": "Carry",
                "x_position": 0.000000,
                "y_position": 0.000000,
                "width": width,
                "height": height,
                "hero_ids": get_df_func(df, 1),
            },
            {
                "category_name": "Mid",
                "x_position": 0.000000,
                "y_position": (height + margin) * 1,
                "width": width,
                "height": height,
                "hero_ids": get_df_func(df, 2),
            },
            {
                "category_name": "Offlane",
                "x_position": 0.000000,
                "y_position": (height + margin) * 2,
                "width": width,
                "height": height,
                "hero_ids": get_df_func(df, 3),
            },
            {
                "category_name": "Semi-Support",
                "x_position": width + margin,
                "y_position": 0.000000,
                "width": width,
                "height": height,
                "hero_ids": get_df_func(df, 4),
            },
            {
                "category_name": "Full-Support",
                "x_position": width + margin,
                "y_position": (height + margin) * 1,
                "width": width,
                "height": height,
                "hero_ids": get_df_func(df, 5),
            },
            {
                "category_name": "Not-Included",
                "x_position": width + margin,
                "y_position": (height + margin) * 2,
                "width": width,
                "height": height,
                "hero_ids": not_included,
            },
        ],
    }
df_full_facets.sort_values("hero")
df_full_facets[
    (df_full_facets["pos"] == f"pos {5}") & (df_full_facets["matches"] >= 50) & (df_full_facets["wr"] > 51)
].sort_values(["wr"], ascending=False)
def make_config_facet(df, name, settings_num=1):
    max_height = 570
    max_width = 1180 - 100
    margin = 20
    width = max_width / 5 - margin
    height = max_height / 2 - margin
    
    height_3 = (max_height / 5) - 20
    width_3 = 70
    
    arr_df = []
    for position in [1,2,3,4,5]:
        if settings_num == 1:
            arr_df.append(df[
                (df["pos"] == f"pos {position}") & (df["matches"] > 200) & (df["wr"] > 51)
            ].sort_values(["wr"], ascending=False))
        if settings_num == 2:
            arr_df.append(df[
                (df["pos"] == f"pos {position}") & (df["matches"] > 50) & (df["wr"] > 51)
            ].sort_values(["wr"], ascending=False))
        
    return {
        "config_name": name,
        "categories": [
            {
                "category_name": "Carry Facet 1",
                "x_position": (width + margin) * 0,
                "y_position": (height + margin) * 0,
                "width": width,
                "height": height,
                "hero_ids": arr_df[0][arr_df[0]["facet_id"] == 0]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Mid Facet 1",
                "x_position": (width + margin) * 1,
                "y_position": (height + margin) * 0,
                "width": width,
                "height": height,
                "hero_ids": arr_df[1][arr_df[1]["facet_id"] == 0]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Offlane Facet 1",
                "x_position": (width + margin) * 2,
                "y_position": (height + margin) * 0,
                "width": width,
                "height": height,
                "hero_ids": arr_df[2][arr_df[2]["facet_id"] == 0]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Semi-Support Facet 1",
                "x_position": (width + margin) * 3,
                "y_position": (height + margin) * 0,
                "width": width,
                "height": height,
                "hero_ids": arr_df[3][arr_df[3]["facet_id"] == 0]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Full-Support Facet 1",
                "x_position": (width + margin) * 4,
                "y_position": (height + margin) * 0,
                "width": width,
                "height": height,
                "hero_ids": arr_df[4][arr_df[4]["facet_id"] == 0]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Carry Facet 2",
                "x_position": (width + margin) * 0,
                "y_position": (height + margin) * 1,
                "width": width,
                "height": height,
                "hero_ids": arr_df[0][arr_df[0]["facet_id"] == 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Mid Facet 2",
                "x_position": (width + margin) * 1,
                "y_position": (height + margin) * 1,
                "width": width,
                "height": height,
                "hero_ids": arr_df[1][arr_df[1]["facet_id"] == 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Offlane Facet 2",
                "x_position": (width + margin) * 2,
                "y_position": (height + margin) * 1,
                "width": width,
                "height": height,
                "hero_ids": arr_df[2][arr_df[2]["facet_id"] == 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Semi-Support Facet 2",
                "x_position": (width + margin) * 3,
                "y_position": (height + margin) * 1,
                "width": width,
                "height": height,
                "hero_ids": arr_df[3][arr_df[3]["facet_id"] == 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "Full-Support Facet 2",
                "x_position": (width + margin) * 4,
                "y_position": (height + margin) * 1,
                "width": width,
                "height": height,
                "hero_ids": arr_df[4][arr_df[4]["facet_id"] == 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "pos1 F 3+",
                "x_position": max_width + margin,
                "y_position": 0.000000,
                "width": width_3,
                "height": height_3,
                "hero_ids": arr_df[0][arr_df[0]["facet_id"] > 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "pos2 F 3+",
                "x_position": max_width + margin,
                "y_position": (height_3 + margin) * 1,
                "width": width_3,
                "height": height_3,
                "hero_ids": arr_df[1][arr_df[1]["facet_id"] > 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "pos3 F 3+",
                "x_position": max_width + margin,
                "y_position": (height_3 + margin) * 2,
                "width": width_3,
                "height": height_3,
                "hero_ids": arr_df[2][arr_df[2]["facet_id"] > 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "pos4 F 3+",
                "x_position": max_width + margin,
                "y_position": (height_3 + margin) * 3,
                "width": width_3,
                "height": height_3,
                "hero_ids": arr_df[3][arr_df[3]["facet_id"] > 1]["hero_id"].values.tolist(),
            },
            {
                "category_name": "pos5 F 3+",
                "x_position": max_width + margin,
                "y_position": (height_3 + margin) * 4,
                "width": width_3,
                "height": height_3,
                "hero_ids": arr_df[4][arr_df[4]["facet_id"] > 1]["hero_id"].values.tolist(),
            },
        ],
    }
df = df_full
position = 5
(
    df[
        (df["pos"] == f"pos {position}") & (df["matches"] > 200) & (df["wr"] > 50)
    ].sort_values(["matches"], ascending=False)
)
def filer_heroes(df, pos=1, matches=0, wr=0, sort_by="wr"):
    return df[
        (df["pos"] == f"pos {pos}") & (df["matches"] > matches) & (df["wr"] > wr)
    ].sort_values([sort_by], ascending=False)
df = df_full
filer_heroes(df, 5, 200, 0, "matches")
df = df_full
position = 5
df[
    (df["pos"] == f"pos {position}") 
    & (df["matches"] > 200) 
    & (df["wr"] > 50)
].sort_values(["wr"], ascending=False)
def get_by_rating(df: pd.DataFrame, position: int):
    return (
        df[(df["pos"] == f"pos {position}") & (df["matches"] > 200)]
        .sort_values(["rating"], ascending=False)["hero_id"]
        .values
        .tolist()
    )
def get_expert(df: pd.DataFrame, position: int):
    return (
        df[
            (df["pos"] == f"pos {position}")
            & (df["expertmatches"] > 20)
            & (df["expert"] > 55)
            & (df["matches"] > 100)
        ]
        .sort_values(["expert"], ascending=False)["hero_id"]
        .values.tolist()
    )
def get_popular(df: pd.DataFrame, position: int):
    return (
        df[(df["pos"] == f"pos {position}") & (df["matches"] > 200)]
        .sort_values(["matches"], ascending=False)["hero_id"]
        .values
        .tolist()
    )
def get_wr(df: pd.DataFrame, position: int):
    return (
        df[(df["pos"] == f"pos {position}") & (df["matches"] > 200) & (df["wr"] > 50)]
        .sort_values(["wr"], ascending=False)["hero_id"]
        .values
        .tolist()
    )
config = {
    "version": 3,
    "configs": [
        make_config_facet(df_full_facets, "Facets matches>200"),
        make_config_facet(df_full_facets, "Facets All", 2),
        make_config(get_wr, df_full, "Win rate"),
        make_config(get_popular, df_full, "Popularity"),
        make_config(get_by_rating, df_full, "D2PT Rating"),
    ],
}
driver.quit()
## Find Steam
import os
import winreg
import win32api

def read_reg(ep, p = r"", k = ''):
    try:
        key = winreg.OpenKeyEx(ep, p)
        value = winreg.QueryValueEx(key,k)
        if key:
            winreg.CloseKey(key)
        return value[0]
    except Exception as e:
        return None
    return None

Path1 = "{}\\Microsoft\\Windows\\Start Menu\\Programs\\Steam\\Steam.lnk".format(os.getenv('APPDATA'))
if os.path.exists(Path1):
    import sys
    import win32com.client 

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(Path1)
    Path1Res = shortcut.Targetpath
else:
    Path1Res = False
Path2 = str(read_reg(ep = winreg.HKEY_LOCAL_MACHINE, p = r"SOFTWARE\Wow6432Node\Valve\Steam", k = 'InstallPath'))+r"\steam.exe"
Path3 = str(read_reg(ep = winreg.HKEY_LOCAL_MACHINE, p = r"SOFTWARE\Valve\Steam", k = 'InstallPath'))+r"\steam.exe"
if not os.path.exists(Path2):
    Path2 = None
if not os.path.exists(Path3):
    Path3 = None
PossiblePaths = [r"X:\Steam\steam.exe", r"X:\Program Files\Steam\steam.exe", r"X:\Program Files (x86)\Steam\steam.exe"]
ValidHardPaths = []
for Drive in win32api.GetLogicalDriveStrings().split('\000')[:-1]:
    Drive = Drive.replace(':\\', '')
    for path in PossiblePaths:
        path = path.replace("X", Drive)
        if os.path.exists(path):
            ValidHardPaths.append(path)
if len(ValidHardPaths) == 0:
    ValidHardPaths = ["None"]
ValidHardPaths
steam_dir = os.path.dirname(os.path.realpath(ValidHardPaths[0]))
steam_dir = os.path.join(steam_dir, "userdata")
steam_dir
dirs_to_check = [os.path.join(steam_dir, id, "570", "remote", "cfg") for id in os.listdir(steam_dir)]
cfg_dirs = [dir for dir in dirs_to_check if os.path.isdir(dir)]
cfg_dirs
for dir in cfg_dirs:
    with open(os.path.join(dir, "hero_grid_config.json"), 'w+') as f:
        json.dump(dict(config), f)
## Autorun
import getpass
import os
import sys
USER_NAME = getpass.getuser()
from win32com.client import Dispatch

bat_path = rf'C:\Users\{USER_NAME}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\{os.path.basename(sys.executable)}.lnk'
target = sys.executable

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(bat_path)
shortcut.Targetpath = target
shortcut.save()
print("Done!")

for remaining in range(2, 0, -1):
    time.sleep(1)