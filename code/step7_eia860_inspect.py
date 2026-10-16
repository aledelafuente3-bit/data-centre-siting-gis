#!/usr/bin/env python3
"""Step 7a: Inspect EIA-860 Excel header rows to find correct skiprows."""
import pandas as pd

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
EIA_DIR = f"{BASE}/02_power_grid/raw/eia860_power_plants/eia8602024"

print("=== 2___Plant_Y2024.xlsx ===")
for n in range(5):
    df = pd.read_excel(f"{EIA_DIR}/2___Plant_Y2024.xlsx", nrows=3, skiprows=n, engine='openpyxl')
    cols = list(df.columns[:8])
    print(f"  skiprows={n}: {cols}")

print("\n=== 3_1_Generator_Y2024.xlsx ===")
for n in range(5):
    df = pd.read_excel(f"{EIA_DIR}/3_1_Generator_Y2024.xlsx", nrows=3, skiprows=n, engine='openpyxl')
    cols = list(df.columns[:8])
    print(f"  skiprows={n}: {cols}")
