import os
import pandas as pd

print("=" * 60)
print("EXTRACTING POWER PLANT DATA")
print("=" * 60)

plant_file = "Methods/1.RawData/Grid/eia8602024/2___Plant_Y2024.xlsx"

print("\nReading Excel file...")
df = pd.read_excel(plant_file, sheet_name=0, header=1)

# Clean column names
df.columns = [str(c).strip() for c in df.columns]

print(f"✓ Loaded {len(df)} rows from EIA data")

# ✅ State column is exactly called "State"
state_col = "State"

print(f"✓ Using state column: {state_col}")

# Filter to your 7 states
state_codes = ["OR", "TX", "VA", "AZ", "IL", "IA", "WV"]
df_filtered = df[df[state_col].isin(state_codes)].copy()
print(f"✓ Filtered to {len(df_filtered)} plants in study area")

# Remove plants without coordinates
df_filtered = df_filtered.dropna(subset=["Latitude", "Longitude"])
print(f"✓ {len(df_filtered)} plants have valid coordinates")

# Keep columns for GIS
df_clean = df_filtered[
    ["Plant Code", "Plant Name", "State", "County", "Latitude", "Longitude"]
].copy()

# Save CSV
output_csv = "Methods/2.ProcessedData/power_plants_study_area.csv"
os.makedirs(os.path.dirname(output_csv), exist_ok=True)

df_clean.to_csv(output_csv, index=False)
print(f"\n✓ Saved CSV to: {output_csv}")

print("\n✅ EXTRACTION COMPLETE!")
print(f"Total plants extracted: {len(df_clean)}")
print(f"Next step: Import '{output_csv}' into QGIS")
