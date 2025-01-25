import pandas as pd
import os

def save_data(df, filename="dota2_meta_data.csv"):
    output_path = os.path.join(os.getcwd(), filename)
    df.to_csv(output_path, index=False)
    print(f"Data saved to {output_path}")

# Использование:
# save_data(df_full)

import pandas as pd
import os

def save_to_csv(df, filename="facet_data.csv"):
    output_path = os.path.join(os.getcwd(), filename)
    df.to_csv(output_path, index=False)
    print(f"Данные сохранены в {output_path}")
