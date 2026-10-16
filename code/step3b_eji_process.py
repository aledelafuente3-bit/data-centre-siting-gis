#!/usr/bin/env python3
"""Step 3b: Convert EJI GeoJSON → GPKG EPSG:5070 → rasterize key fields."""
import os, json, subprocess

os.environ['PROJ_LIB']  = '/Applications/QGIS-LTR.app/Contents/Resources/proj'
os.environ['PROJ_DATA'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj'

from osgeo import ogr, osr, gdal
gdal.UseExceptions()

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
EJI_JSON = f"{BASE}/01_RAW_DATA/social_equity/eji_2024/eji_2022_7states.geojson"
OUT_GPKG = f"{BASE}/11_processed_layers/eji_2024_7states_EPSG5070.gpkg"
RAST_DIR = f"{BASE}/11_processed_layers/rasters"
MASK     = f"{RAST_DIR}/mask_7states_1km_EPSG5070.tif"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"

# ─── A. Convert GeoJSON → GPKG in EPSG:5070 ────────────────────────────────
print("=== A: Converting GeoJSON → GPKG (EPSG:5070) ===")
if os.path.exists(OUT_GPKG):
    os.remove(OUT_GPKG)

result = subprocess.run([
    f"{GDAL_BIN}/ogr2ogr",
    "-f", "GPKG",
    "-t_srs", "EPSG:5070",
    OUT_GPKG, EJI_JSON
], capture_output=True, text=True)
if result.returncode != 0:
    print("ERROR:", result.stderr[:200])
else:
    print("Done")

# Check output
result2 = subprocess.run(
    [f"{GDAL_BIN}/ogrinfo", "-al", "-so", OUT_GPKG],
    capture_output=True, text=True
)
for line in result2.stdout.split('\n'):
    if any(k in line for k in ['Feature Count', 'Extent', 'Layer SRS', 'PROJCS', 'GEOGCS']):
        print(f"  {line.strip()}")

print(f"Saved: {OUT_GPKG}")

# ─── B. Rasterize key EJI fields to 1km ────────────────────────────────────
# Fields to rasterize:
#   rpl_eji = overall EJI ranked percentile (0–1)
#   rpl_ebm = environmental burden module
#   rpl_svm = social vulnerability module  
#   rpl_hvm = health vulnerability module (if exists)
print("\n=== B: Rasterizing EJI fields ===")

EJI_FIELDS = {
    'eji_2024_score_1km':   'rpl_eji',   # overall
    'eji_2024_envburd_1km': 'rpl_ebm',   # environmental burden
    'eji_2024_socvuln_1km': 'rpl_svm',   # social vulnerability
}

# Check which fields exist
ds = ogr.Open(OUT_GPKG)
lyr = ds.GetLayer(0)
defn = lyr.GetLayerDefn()
avail_fields = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
ds = None
print(f"Available EJI fields: {[f for f in avail_fields if any(k in f for k in ['rpl_','spl_'])][:10]}")

for out_name, field in EJI_FIELDS.items():
    if field not in avail_fields:
        print(f"  SKIP {field} — not found")
        continue
    out_tif = f"{RAST_DIR}/{out_name}.tif"
    print(f"  Rasterizing {field} → {out_name}.tif")
    
    r = subprocess.run([
        f"{GDAL_BIN}/gdal_rasterize",
        "-a", field,
        "-init", "-9999",
        "-a_nodata", "-9999",
        "-ot", "Float32",
        "-te", "-2295000", "310000", "1791000", "2907000",
        "-tr", "1000", "1000",
        "-co", "COMPRESS=LZW",
        OUT_GPKG, out_tif
    ], capture_output=True, text=True)
    
    if r.returncode == 0:
        # Quick stats
        r2 = subprocess.run(
            [f"{GDAL_BIN}/gdalinfo", "-mm", out_tif],
            capture_output=True, text=True
        )
        for line in r2.stdout.split('\n'):
            if 'Min/Max' in line:
                print(f"    {line.strip()}")
    else:
        print(f"  ERROR: {r.stderr[:100]}")

# ─── C. Compute within-7-state P75 flag ────────────────────────────────────
print("\n=== C: Computing within-7-state P75 flag for rpl_eji ===")
import numpy as np

SCORE_TIF = f"{RAST_DIR}/eji_2024_score_1km.tif"
MASK_TIF  = MASK
FLAG_TIF  = f"{RAST_DIR}/eji_2024_flag_p75_1km.tif"

if os.path.exists(SCORE_TIF):
    score_ds = gdal.Open(SCORE_TIF)
    mask_ds  = gdal.Open(MASK_TIF)
    score_arr = score_ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    mask_arr  = mask_ds.GetRasterBand(1).ReadAsArray()
    
    valid_vals = score_arr[(mask_arr == 1) & (score_arr > -9998)]
    p75 = float(np.percentile(valid_vals, 75))
    print(f"  Within-7-state P75 of rpl_eji: {p75:.4f}")
    print(f"  N valid cells: {len(valid_vals):,}")
    
    # Create flag raster: 1 = ≥ P75 (high EJ concern), 0 = below P75, -9999 = NoData
    flag_arr = np.where(mask_arr == 1,
                        np.where(score_arr > -9998, (score_arr >= p75).astype(np.float32), -9999),
                        -9999)
    
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(FLAG_TIF, score_ds.RasterXSize, score_ds.RasterYSize,
                           1, gdal.GDT_Float32,
                           options=['COMPRESS=LZW'])
    out_ds.SetGeoTransform(score_ds.GetGeoTransform())
    out_ds.SetProjection(score_ds.GetProjection())
    band = out_ds.GetRasterBand(1)
    band.WriteArray(flag_arr)
    band.SetNoDataValue(-9999)
    out_ds.FlushCache(); out_ds = None
    
    # Count flagged cells
    n_flagged = int((flag_arr == 1).sum())
    n_valid   = int((mask_arr == 1).sum())
    print(f"  Cells flagged as high-concern (≥ P75): {n_flagged:,} ({100*n_flagged/n_valid:.1f}% of study area)")
    print(f"  Saved: {FLAG_TIF}")
else:
    print("  rpl_eji raster not found, skipping P75 flag")

print("\n=== Step 3 EJI processing complete ===")
print("Outputs:")
for f in ['eji_2024_7states_EPSG5070.gpkg', 'eji_2024_score_1km.tif', 
          'eji_2024_envburd_1km.tif', 'eji_2024_socvuln_1km.tif', 'eji_2024_flag_p75_1km.tif']:
    path = f"{OUT_GPKG if f.endswith('.gpkg') else RAST_DIR}/{f}"
    if os.path.exists(path):
        print(f"  {f}: {os.path.getsize(path)/1024/1024:.1f} MB")
    else:
        print(f"  {f}: NOT FOUND")
