#!/usr/bin/env python3
"""
Step 7: EIA-860 Power Plant Layer Rebuild — OP-only generators
"""
import pandas as pd

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
EIA_DIR = f"{BASE}/02_power_grid/raw/eia860_power_plants/eia8602024"
OUT_CSV = f"{EIA_DIR}/plants_7state_operating_2024.csv"
SEVEN_STATES = ['AZ', 'IL', 'IA', 'OR', 'TX', 'VA', 'WV']

# ─── 1. Plant file ─────────────────────────────────────────────────────────────
df_plant = pd.read_excel(f"{EIA_DIR}/2___Plant_Y2024.xlsx", skiprows=1, engine='openpyxl')
df_plant.columns = df_plant.columns.str.strip()
df_plant = df_plant.rename(columns={
    'Utility ID':'utility_id','Utility Name':'utility_name','Plant Code':'plant_code',
    'Plant Name':'plant_name','State':'state','County':'county','Latitude':'latitude',
    'Longitude':'longitude','Balancing Authority Code':'ba_code',
    'Balancing Authority Name':'ba_name','NERC Region':'nerc_region',
    'Grid Voltage (kV)':'grid_voltage_kv',
})
keep = ['plant_code','plant_name','state','county','utility_id','utility_name',
        'ba_code','ba_name','nerc_region','grid_voltage_kv','latitude','longitude']
df_plant = df_plant[[c for c in keep if c in df_plant.columns]]
df_plant = df_plant[df_plant['state'].isin(SEVEN_STATES)].copy()

# ─── 2. Generator file — OP status only ────────────────────────────────────────
df_gen = pd.read_excel(f"{EIA_DIR}/3_1_Generator_Y2024.xlsx", skiprows=1, engine='openpyxl')
df_gen.columns = df_gen.columns.str.strip()
df_gen = df_gen.rename(columns={
    'Plant Code':'plant_code','Generator ID':'generator_id',
    'Nameplate Capacity (MW)':'nameplate_mw','Energy Source 1':'energy_source_1',
    'Technology':'technology','Prime Mover':'prime_mover','Status':'status',
    'Summer Capacity (MW)':'summer_capacity_mw',
})
df_gen['nameplate_mw'] = pd.to_numeric(df_gen['nameplate_mw'], errors='coerce')

# Filter to operating status only
df_gen_op = df_gen[df_gen['status'] == 'OP'].copy()
print(f"Operating generators nationally: {len(df_gen_op)}")

def primary_fuel(s):
    vals = [v for v in s if pd.notna(v) and str(v).strip() not in ('','nan')]
    return max(set(vals), key=vals.count) if vals else None

def fuel_list(s):
    return '|'.join(sorted(set(str(v).strip() for v in s
                             if pd.notna(v) and str(v).strip() not in ('','nan'))))

def tech_list(s):
    return '|'.join(sorted(set(str(v).strip() for v in s
                             if pd.notna(v) and str(v).strip() not in ('','nan'))))

agg_dict = {
    'nameplate_mw_total': ('nameplate_mw', 'sum'),
    'generator_count':    ('generator_id', 'count'),
    'primary_fuel':       ('energy_source_1', primary_fuel),
    'fuel_types':         ('energy_source_1', fuel_list),
}
if 'technology' in df_gen_op.columns:
    agg_dict['technologies'] = ('technology', tech_list)

df_gen_agg = df_gen_op.groupby('plant_code').agg(**agg_dict).reset_index()

# ─── 3. Join ───────────────────────────────────────────────────────────────────
df_merged = df_plant.merge(df_gen_agg, on='plant_code', how='left')

print(f"7-state plants total:           {len(df_merged)}")
print(f"  With operating generators:    {df_merged['nameplate_mw_total'].notna().sum()}")
print(f"  Without generators (site-only or retired at plant level): {df_merged['nameplate_mw_total'].isna().sum()}")
print(f"  Total nameplate capacity (MW):{df_merged['nameplate_mw_total'].sum():.0f}")
print(f"\nCapacity by state (MW):")
print(df_merged.groupby('state')['nameplate_mw_total'].sum().sort_values(ascending=False).to_string())
print(f"\nTop fuels by plant count:")
print(df_merged['primary_fuel'].value_counts().head(15).to_string())
print(f"\nPlants by state:")
print(df_merged['state'].value_counts().to_string())

df_merged.to_csv(OUT_CSV, index=False)
print(f"\nSaved: {OUT_CSV} ({len(df_merged)} rows, {len(df_merged.columns)} columns)")
