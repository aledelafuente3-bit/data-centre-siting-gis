#!/usr/bin/env python3
"""
step1_padus_process.py
PAD-US 4.0 — GAP 1+2 hard-exclusion raster + GAP 3 planning-review flag

VERSION: PAD-US 4.0 (NOT 4.1)
Source:  USGS GAP Analysis Project, ScienceBase item 652d4f80d34e44db0e2ee45c
Layer:   PADUS4_0Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_{ABBR}

Outputs (no /tmp paths — all in project dir):
  11_processed_layers/rasters/pad_us_gap12_exclusion_1km.tif
  11_processed_layers/rasters/pad_us_gap3_flag_1km.tif
  11_processed_layers/pad_us_40_gap12_EPSG5070.gpkg
  11_processed_layers/pad_us_40_gap3_EPSG5070.gpkg
"""

import os, subprocess, glob, sys, time
import numpy as np
from pathlib import Path

GDAL     = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
PAD_RAW  = f"{BASE}/08_protected_areas_and_land_cover/raw/pad_us"
PROC     = f"{BASE}/11_processed_layers"
RAST     = f"{PROC}/rasters"
TMP      = "/tmp/padus_work"
TE       = "-2295000 310000 1791000 2907000"

os.makedirs(TMP, exist_ok=True)
os.makedirs(RAST, exist_ok=True)

def run(cmd, check=True, capture=True):
    r = subprocess.run(cmd, capture_output=capture, text=True,
                       shell=isinstance(cmd, str))
    if check and r.returncode != 0 and capture:
        print(f"  WARN: {r.stderr[:200]}")
    return r

print("=== Step 1: PAD-US 4.0 Processing ===")
print("Source: USGS GAP Analysis Project PAD-US 4.0")
print("ScienceBase: https://www.sciencebase.gov/catalog/item/652d4f80d34e44db0e2ee45c")

# ─── A. Unzip ─────────────────────────────────────────────────────────────────
print("\n--- A: Unzipping state GDB ZIPs ---")
zips = sorted(glob.glob(f"{PAD_RAW}/PADUS4_0_State_*_GDB.zip"))
print(f"  Found {len(zips)} ZIP files")

for zf in zips:
    state = Path(zf).stem.replace("PADUS4_0_State_", "").replace("_GDB", "")
    out_dir = f"{TMP}/pad_{state}"
    if not os.path.isdir(out_dir):
        print(f"  Unzipping {state}...")
        subprocess.run(["unzip", "-q", zf, "-d", out_dir], check=True)
    else:
        print(f"  {state}: already unzipped")

# Find GDB directories (GDBs are directories, not files)
gdb_dirs = sorted(Path(TMP).glob("**/*.gdb"))
gdb_dirs = [str(g) for g in gdb_dirs if g.is_dir()]
print(f"\n  Found {len(gdb_dirs)} GDB directories:")
for g in gdb_dirs:
    print(f"    {g}")

if not gdb_dirs:
    print("ERROR: No GDB directories found — check unzip output")
    sys.exit(1)

# ─── B. Identify combined layer ───────────────────────────────────────────────
print("\n--- B: Verifying combined layer and GAP_Sts values ---")
sample_gdb = gdb_dirs[0]
r = run([f"{GDAL}/ogrinfo", sample_gdb])
layers = []
for line in r.stdout.split("\n"):
    if "Comb" in line:
        name = line.strip().split(": ", 1)[-1].split(" (")[0]
        layers.append(name)
if layers:
    print(f"  Combined layer found: {layers[0]}")
else:
    print(f"  ERROR: Could not find 'Comb' layer in {sample_gdb}")
    # List all layers for debugging
    for line in r.stdout.split("\n"):
        if line.strip().startswith(tuple("0123456789")):
            print(f"    {line.strip()}")
    sys.exit(1)

# Check GAP_Sts values
sample_layer = layers[0]
r2 = run([f"{GDAL}/ogrinfo", sample_gdb, "-sql",
          f'SELECT DISTINCT GAP_Sts FROM "{sample_layer}" ORDER BY GAP_Sts'])
vals = [l.strip() for l in r2.stdout.split("\n") if "GAP_Sts" in l and "(String)" in l]
print(f"  GAP_Sts values: {[v.split('= ')[-1] for v in vals]}")

# ─── C. Merge GAP 1+2 across all states ──────────────────────────────────────
print("\n--- C: Merging GAP Status 1+2 (hard exclusion) ---")
GAP12_GPKG = f"{PROC}/pad_us_40_gap12_EPSG5070.gpkg"
if os.path.exists(GAP12_GPKG):
    os.remove(GAP12_GPKG)

for i, gdb in enumerate(gdb_dirs):
    # Extract state abbreviation from GDB directory name
    gdb_name = Path(gdb).name          # e.g. PADUS4_0_StateAZ.gdb
    state_abb = gdb_name.replace("PADUS4_0_State", "").replace(".gdb", "")
    # Construct combined layer name
    layer = f"PADUS4_0Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_{state_abb}"

    print(f"  {state_abb} ({i+1}/{len(gdb_dirs)}): layer = {layer}")

    if i == 0:
        run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:5070",
             "-where", "GAP_Sts IN ('1','2')",
             "-nln", "padus_gap12",
             GAP12_GPKG, gdb, layer])
    else:
        run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:5070",
             "-where", "GAP_Sts IN ('1','2')",
             "-nln", "padus_gap12", "-append", "-update",
             GAP12_GPKG, gdb, layer])

r = run([f"{GDAL}/ogrinfo", "-al", "-so", GAP12_GPKG])
for line in r.stdout.split("\n"):
    if "Feature Count" in line or "Extent" in line:
        print(f"  {line.strip()}")

# Save copy in raw dir
import shutil
shutil.copy2(GAP12_GPKG, f"{PAD_RAW}/pad_us_40_gap12_EPSG5070.gpkg")
print(f"  Saved copy to {PAD_RAW}/pad_us_40_gap12_EPSG5070.gpkg")

# ─── D. Rasterize GAP 1+2 ────────────────────────────────────────────────────
print("\n--- D: Rasterizing GAP 1+2 → 1km binary raster ---")
OUT12 = f"{RAST}/pad_us_gap12_exclusion_1km.tif"
run([f"{GDAL}/gdal_rasterize",
     "-burn", "1", "-init", "0",
     "-ot", "Byte", "-a_nodata", "255",
     "-te"] + TE.split() + [
     "-tr", "1000", "1000",
     "-co", "COMPRESS=LZW",
     GAP12_GPKG, OUT12])
r = run([f"{GDAL}/gdalinfo", "-mm", OUT12])
for line in r.stdout.split("\n"):
    if any(x in line for x in ["EPSG", "Pixel Size", "NoData", "Min/Max", "5070"]):
        print(f"  {line.strip()}")

# ─── E. Merge GAP 3 ──────────────────────────────────────────────────────────
print("\n--- E: Merging GAP Status 3 (planning-review flag) ---")
GAP3_GPKG = f"{PROC}/pad_us_40_gap3_EPSG5070.gpkg"
if os.path.exists(GAP3_GPKG):
    os.remove(GAP3_GPKG)

for i, gdb in enumerate(gdb_dirs):
    gdb_name = Path(gdb).name
    state_abb = gdb_name.replace("PADUS4_0_State", "").replace(".gdb", "")
    layer = f"PADUS4_0Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_{state_abb}"
    print(f"  {state_abb} GAP3...")
    if i == 0:
        run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:5070",
             "-where", "GAP_Sts = '3'",
             "-nln", "padus_gap3",
             GAP3_GPKG, gdb, layer])
    else:
        run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:5070",
             "-where", "GAP_Sts = '3'",
             "-nln", "padus_gap3", "-append", "-update",
             GAP3_GPKG, gdb, layer])

r = run([f"{GDAL}/ogrinfo", "-al", "-so", GAP3_GPKG])
for line in r.stdout.split("\n"):
    if "Feature Count" in line:
        print(f"  {line.strip()}")
shutil.copy2(GAP3_GPKG, f"{PAD_RAW}/pad_us_40_gap3_EPSG5070.gpkg")

# ─── F. Rasterize GAP 3 ──────────────────────────────────────────────────────
print("\n--- F: Rasterizing GAP 3 → 1km flag raster ---")
OUT3 = f"{RAST}/pad_us_gap3_flag_1km.tif"
run([f"{GDAL}/gdal_rasterize",
     "-burn", "1", "-init", "0",
     "-ot", "Byte", "-a_nodata", "255",
     "-te"] + TE.split() + [
     "-tr", "1000", "1000",
     "-co", "COMPRESS=LZW",
     GAP3_GPKG, OUT3])
r = run([f"{GDAL}/gdalinfo", "-mm", OUT3])
for line in r.stdout.split("\n"):
    if any(x in line for x in ["EPSG", "Pixel Size", "NoData", "Min/Max", "5070"]):
        print(f"  {line.strip()}")

# ─── G. Known-place QC checks ─────────────────────────────────────────────────
print("\n--- G: QC — known protected area checks ---")
checks = [
    (-112.1, 36.1, "Grand Canyon NP      AZ", 1),
    (-88.8,  37.5, "Shawnee NF           IL", 1),
    (-78.4,  38.5, "Shenandoah NP        VA", 1),
    (-122.1, 42.9, "Crater Lake NP       OR", 1),
    (-79.8,  38.5, "Monongahela NF       WV", 1),
    (-93.6,  41.6, "Des Moines IA urban  IA", 0),  # control (should be 0)
]
for lon, lat, name, expected in checks:
    r = run([f"{GDAL}/gdallocationinfo", "-wgs84", OUT12, str(lon), str(lat)])
    val = None
    for line in r.stdout.split("\n"):
        if "Value" in line:
            val = line.strip().split(":")[-1].strip()
    ok = "✅" if val == str(expected) else "⚠️ CHECK"
    print(f"  {ok} {name} ({lon},{lat}): got={val}, expected={expected}")

# ─── H. Distribution stats ────────────────────────────────────────────────────
print("\n--- H: Distribution stats within 7-state mask ---")
try:
    from osgeo import gdal
    gdal.UseExceptions()
    mask_arr = gdal.Open(f"{RAST}/mask_7states_1km_EPSG5070.tif").GetRasterBand(1).ReadAsArray()
    n_mask = int((mask_arr == 1).sum())
    print(f"  Mask valid cells: {n_mask:,}")

    for path, label in [(OUT12, "GAP 1+2 hard-exclusion"), (OUT3, "GAP 3 flag")]:
        ds = gdal.Open(path)
        arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        nd = ds.GetRasterBand(1).GetNoDataValue()
        valid = arr[(mask_arr == 1) & ((arr != nd) if nd is not None else True)]
        n_excl = int((valid == 1).sum())
        pct = 100.0 * n_excl / n_mask
        proj = ds.GetProjection()
        gt = ds.GetGeoTransform()
        epsg = "EPSG:5070 ✅" if "5070" in proj else "CHECK CRS"
        pixel = abs(gt[1])
        print(f"  {label}: {n_excl:,} cells = {pct:.2f}% of study area")
        print(f"    CRS: {epsg} | Pixel: {pixel:.0f}m | NoData: {nd}")
except Exception as e:
    print(f"  Stats error: {e}")

print(f"\n=== Step 1 PAD-US 4.0 COMPLETE: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
print("\nOutputs (all in project directory — no /tmp references):")
for f in [OUT12, OUT3, GAP12_GPKG, GAP3_GPKG]:
    if os.path.exists(f):
        sz = os.path.getsize(f) / 1024 / 1024
        print(f"  {f}  ({sz:.1f} MB)")

print("\n⚠️  VERSION NOTE: PAD-US 4.0 (not 4.1)")
print("   Update all methodology text, dissertation, and admin docs to say PAD-US 4.0")
