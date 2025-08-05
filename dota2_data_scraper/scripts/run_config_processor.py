import pandas as pd
import os
import json
from modules.hero_config import HeroConfigProcessor
from scripts.cleanup import save_to_csv
from modules.steam_config import backup_and_save_config
from modules.webdriver_cleanup import quit_driver
from modules.config_manager import get_chrome_driver
from modules.autostart_manager import add_to_startup

# Проверяем наличие файлов данных
if not os.path.exists("heroes_data.csv") or not os.path.exists("all_facets_data.csv"):
    raise FileNotFoundError(
        "Ошибка: heroes_data.csv или all_facets_data.csv не найдены! Запустите run_scraper.py и run_facet_scraper.py."
    )

# Загружаем основные данные (df_full) и фасеты (df_full_facets)
df_full = pd.read_csv("heroes_data.csv")
df_full_facets = pd.read_csv("facets_data.csv")
all_facets_df = pd.read_csv("all_facets_data.csv")


# Обработка данных героев (df_final)
all_facets_df_unique = all_facets_df.drop_duplicates(
    subset=["localized_name"], keep="first"
)
df_final = pd.merge(
    df_full,
    all_facets_df_unique[["id", "localized_name"]],
    left_on=["Hero"],
    right_on=["localized_name"],
    how="left",
)


# Переименовываем столбец id -> hero_id
df_final.rename(columns={"id": "hero_id"}, inplace=True)

# Перемещаем "hero_id" на нулевую позицию
cols = ["hero_id"] + [col for col in df_final.columns if col != "hero_id"]
df_final = df_final[cols]

# Исправляем идентификатор героя "Outworld Destroyer"
df_final.loc[df_final["Hero"] == "Outworld Destroyer", "hero_id"] = 76

# Обработка столбцов Expert и WR 9500+ MMR
# df_final["Expert Win Rate"] = (
#     df_final["Expert"].astype(str).str.extract(r"(\d+\.\d+)").astype(float)
# )
# df_final["Expert Matches"] = df_final["Expert"].str.extract(r"\((\d+)\)").astype(int)
# df_final["9500 Win Rate"] = (
#     df_final["WR 9500+ MMR"].str.extract(r"(\d+\.\d+)%").astype(float)
# )
# df_final["9500 Matches"] = df_final["WR 9500+ MMR"].str.extract(r" (\d+) ").astype(int)

# df_final.drop(columns=["Expert", "WR 9500+ MMR"], inplace=True)

# Обработка данных фасетов (df_final_facets)
df_full_facets["facet_upper"] = df_full_facets["Facet"].str.upper()
all_facets_df["name_upper"] = all_facets_df["name"].str.upper()

df_final_facets = pd.merge(
    df_full_facets,
    all_facets_df[["facet_number", "id", "name_upper", "localized_name"]],
    left_on=["facet_upper", "Hero"],
    right_on=["name_upper", "localized_name"],
    how="left",
)

df_final_facets.drop(columns=["facet_upper", "name_upper"], inplace=True)
df_final_facets.rename(columns={"id": "hero_id"}, inplace=True)

cols = ["hero_id"] + [col for col in df_final_facets.columns if col != "hero_id"]
df_final_facets = df_final_facets[cols]

df_final_facets = df_final_facets[
    ["hero_id", "Hero", "Facet", "Matches", "Win Rate", "Role", "facet_number"]
]

# Сохранение финальных файлов
save_to_csv(df_final, "processed_heroes.csv")
save_to_csv(df_final_facets, "processed_facets.csv")

print("Обработанные данные сохранены в processed_heroes.csv и processed_facets.csv")


# Формирование конфигурации
config = {
    "version": 3,
    "configs": [
        # Фасеты
        HeroConfigProcessor(
            df_final_facets, "Facet Matches>200", data_type="facet"
        ).build_config(matches_threshold=200, wr_threshold=51),
        HeroConfigProcessor(
            df_final_facets, "Facet Matches>50", data_type="facet"
        ).build_config(matches_threshold=50, wr_threshold=51),
        # Регулярные конфигурации
        HeroConfigProcessor(df_final, "Win Rate", data_type="regular").build_config(
            matches_threshold=200, wr_threshold=51
        ),
        HeroConfigProcessor(df_final, "D2PT", data_type="regular").build_config(
            matches_threshold=200, wr_threshold=0, sort_by="D2PT Rating"
        ),
        # Эксперты
        HeroConfigProcessor(
            df_final, "Expert Win Rate", data_type="regular"
        ).build_config(
            expert_matches_threshold=50,
            expert_wr_threshold=51,
            sort_by="Expert Win Rate",
        ),
        # 9500 MMR
        HeroConfigProcessor(
            df_final, "9500 Win Rate", data_type="regular"
        ).build_config(
            mmr_9500_matches_threshold=100,
            mmr_9500_wr_threshold=51,
            sort_by="9500 Win Rate",
        ),
    ],
}

with open("hero_configs.json", "w") as config_file:
    json.dump(config, config_file, indent=4)


print("Конфигурация героев успешно сохранена в hero_configs.json")

# Завершение работы WebDriver в фоновом режиме
driver = get_chrome_driver()
quit_driver(driver)

# Обновление конфигурации Dota 2
backup_and_save_config(config)

print("Конфигурация Dota 2 обновлена.")

# Добавляем программу в автозагрузку
add_to_startup()