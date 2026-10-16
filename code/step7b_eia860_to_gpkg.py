#!/usr/bin/env python3
"""Step 7b: Convert EIA-860 CSV to GeoPackage in EPSG:5070"""
import os, sys, csv

# Fix PROJ database path for QGIS Python
os.environ['PROJ_LIB'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj'
os.environ['PROJ_DATA'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj'

from osgeo import ogr, osr

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
CSV_IN  = f"{BASE}/02_power_grid/raw/eia860_power_plants/eia8602024/plants_7state_operating_2024.csv"
GPKG_OUT = f"{BASE}/11_processed_layers/eia860_powerplants_operating_7state_EPSG5070.gpkg"

# CRS setup
src_srs = osr.SpatialReference()
src_srs.ImportFromEPSG(4326)
src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

dst_srs = osr.SpatialReference()
dst_srs.ImportFromEPSG(5070)
dst_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

transform = osr.CoordinateTransformation(src_srs, dst_srs)

# Create output GPKG
driver = ogr.GetDriverByName('GPKG')
if os.path.exists(GPKG_OUT):
    driver.DeleteDataSource(GPKG_OUT)
ds = driver.CreateDataSource(GPKG_OUT)
layer = ds.CreateLayer('eia860_powerplants', srs=dst_srs, geom_type=ogr.wkbPoint)

# Define fields
fields = [
    ('plant_code',           ogr.OFTInteger),
    ('plant_name',           ogr.OFTString),
    ('state',                ogr.OFTString),
    ('county',               ogr.OFTString),
    ('utility_id',           ogr.OFTInteger),
    ('utility_name',         ogr.OFTString),
    ('ba_code',              ogr.OFTString),
    ('ba_name',              ogr.OFTString),
    ('nerc_region',          ogr.OFTString),
    ('grid_voltage_kv',      ogr.OFTReal),
    ('nameplate_mw_total',   ogr.OFTReal),
    ('generator_count',      ogr.OFTInteger),
    ('primary_fuel',         ogr.OFTString),
    ('fuel_types',           ogr.OFTString),
    ('technologies',         ogr.OFTString),
    ('latitude_wgs84',       ogr.OFTReal),
    ('longitude_wgs84',      ogr.OFTReal),
]

for fname, ftype in fields:
    fd = ogr.FieldDefn(fname, ftype)
    if ftype == ogr.OFTString:
        fd.SetWidth(255)
    layer.CreateField(fd)

defn = layer.GetLayerDefn()
added = skipped_nocoord = skipped_bad = 0

def safe_int(v):
    try: return int(float(v)) if v and str(v).strip() not in ('','nan','None') else None
    except: return None

def safe_float(v):
    try: return float(v) if v and str(v).strip() not in ('','nan','None') else None
    except: return None

with open(CSV_IN, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        lat_str = row.get('latitude','').strip()
        lon_str = row.get('longitude','').strip()
        lat = safe_float(lat_str)
        lon = safe_float(lon_str)
        
        if lat is None or lon is None:
            skipped_nocoord += 1
            continue
        if abs(lat) < 1 or abs(lon) < 1 or lat > 90 or abs(lon) > 180:
            skipped_bad += 1
            continue
        
        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint(lon, lat)
        pt.Transform(transform)
        
        feat = ogr.Feature(defn)
        feat.SetGeometry(pt)
        feat.SetField('plant_code',          safe_int(row.get('plant_code')))
        feat.SetField('plant_name',          row.get('plant_name',''))
        feat.SetField('state',               row.get('state',''))
        feat.SetField('county',              row.get('county',''))
        feat.SetField('utility_id',          safe_int(row.get('utility_id')))
        feat.SetField('utility_name',        row.get('utility_name',''))
        feat.SetField('ba_code',             row.get('ba_code',''))
        feat.SetField('ba_name',             row.get('ba_name',''))
        feat.SetField('nerc_region',         row.get('nerc_region',''))
        feat.SetField('grid_voltage_kv',     safe_float(row.get('grid_voltage_kv')))
        feat.SetField('nameplate_mw_total',  safe_float(row.get('nameplate_mw_total')))
        feat.SetField('generator_count',     safe_int(row.get('generator_count')))
        feat.SetField('primary_fuel',        row.get('primary_fuel',''))
        feat.SetField('fuel_types',          row.get('fuel_types',''))
        feat.SetField('technologies',        row.get('technologies',''))
        feat.SetField('latitude_wgs84',      lat)
        feat.SetField('longitude_wgs84',     lon)
        layer.CreateFeature(feat)
        added += 1

ds.FlushCache()
ds = None

print(f"Added:            {added}")
print(f"Skipped no-coord: {skipped_nocoord}")
print(f"Skipped bad-coord:{skipped_bad}")
print(f"Output: {GPKG_OUT}")

# QC
from osgeo import gdal
gdal.UseExceptions()
ds2 = ogr.Open(GPKG_OUT)
lyr = ds2.GetLayer(0)
print(f"\nQC — Feature count: {lyr.GetFeatureCount()}")
print(f"     CRS auth code: {lyr.GetSpatialRef().GetAuthorityCode(None)}")
# Check a few features
for feat in lyr:
    g = feat.GetGeometryRef()
    if g:
        print(f"     Sample: {feat.GetField('plant_name')} ({feat.GetField('state')}) "
              f"X={g.GetX():.0f} Y={g.GetY():.0f} "
              f"MW={feat.GetField('nameplate_mw_total')} "
              f"fuel={feat.GetField('primary_fuel')}")
    if lyr.GetFID(feat) - lyr.GetFeaturesRead() > 5:
        break
ds2 = None
