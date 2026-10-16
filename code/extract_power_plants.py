import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os

print("=" * 60)
print("EXTRACTING POWER PLANT DATA")
print("=" * 60)

# Read the Plant file
plant_file = '1_RawData/Grid/eia8602024/2___Plant_Y2024.xlsx'

# Read all sheets to find the right one
excel_file = pd.ExcelFile(plant_file)
print(f"\nAvailable sheets: {excel_file.sheet_names}")

# Usually the data is in the first sheet or a sheet called 'Plant' or 
'Operable'
# Try the first sheet first
df = pd.read_excel(plant_file, sheet_name=0)

print(f"\n✓ Loaded {len(df)} plants from EIA data")
print(f"Columns found: {df.columns.tolist()[:5]}...")

# Filter to your 7 states
state_codes = ['OR', 'TX', 'VA', 'AZ', 'IL', 'IA', 'WV']
df_filtered = df[df['State'].isin(state_codes)].copy()

print(f"\n✓ Filtered to {len(df_filtered)} plants in study area")

# Remove plants without coordinates
df_filtered = df_filtered.dropna(subset=['Latitude', 'Longitude'])

print(f"✓ {len(df_filtered)} plants have valid coordinates")

# Select only the columns we need
columns_to_keep = [
    'Utility ID',
    'Utility Name', 
    'Plant Code',
    'Plant Name',
    'City',
    'State',
    'County',
    'Latitude',
    'Longitude',
    'Balancing Authority Code',
    'Balancing Authority Name',
    'Sector Name'
]

df_clean = df_filtered[columns_to_keep].copy()

# Create geometry for GIS
geometry = [Point(xy) for xy in zip(df_clean['Longitude'], 
df_clean['Latitude'])]
gdf = gpd.GeoDataFrame(df_clean, geometry=geometry, crs='EPSG:4326')

# Reproject to your analysis CRS (Albers Equal Area)
gdf = gdf.to_crs('EPSG:5070')

# Save as shapefile
output_shp = '2_ProcessedData/Vectors/power_plants_study_area.shp'
gdf.to_file(output_shp)

print(f"\n✓ Saved shapefile to: {output_shp}")

# Also save as CSV for reference
output_csv = '2_ProcessedData/power_plants_study_area.csv'
df_clean.to_csv(output_csv, index=False)

print(f"✓ Saved CSV to: {output_csv}")

# Summary statistics
print("\n" + "=" * 60)
print("SUMMARY BY STATE")
print("=" * 60)
summary = df_clean.groupby('State').agg({
    'Plant Code': 'count',
    'Plant Name': 'first'  # Just to have something
}).rename(columns={'Plant Code': 'Number of Plants'})

print(summary)

print("\n" + "=" * 60)
print("SAMPLE OF EXTRACTED DATA")
print("=" * 60)
print(df_clean[['Plant Name', 'State', 'County', 'Latitude', 
'Longitude']].head(10))

print("\n✅ EXTRACTION COMPLETE!")
print(f"\nNext step: Open QGIS and add the shapefile:")
print(f"  {output_shp}")
