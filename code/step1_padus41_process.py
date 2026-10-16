#!/usr/bin/env python3
"""
step1_padus41_process.py
PAD-US 4.1 — GAP 1+2 hard-exclusion raster + GAP 3 planning-review flag

VERSION: PAD-US 4.1
Source:  USGS GAP Analysis Project, ScienceBase item 6759abcfd34edfeb8710a004
         https://www.sciencebase.gov/catalog/item/6759abcfd34edfeb8710a004
Layer:   PADUS4_1Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_{ABBR}
         (discovered automatically from GDB if name differs)

Input ZIPs expected in:
  08_protected_areas_and_land_cover/raw/pad_us/PADUS4_1_State_AZ_GDB_KMZ.zip
  08_protected_areas_and_land_cover/raw/pad_us/PADUS4_1_State_IL_GDB_KMZ.zip
  ... (same pattern for IA, OR, TX, VA, WV)

Outputs (all in project dir — no /tmp references in final outputs):
  11_processed_layers/rasters/pad_us_gap12_exclusion_1km.tif  ← REPLACES 4.0
  11_processed_layers/rasters/pad_us_gap3_flag_1km.tif        ← REPLACES 4.0
  11_processed_layers/pad_us_41_gap12_EPSG5070.gpkg
  11_processed_layers/pad_us_41_gap3_EPSG5070.gpkg
"""

import os, subprocess, glob, sys, time, shutil
import numpy as np
from pathlib import Path

GDAL     = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
PAD_RAW  = f"{BASE}/08_protected_areas_and_land_cover/raw/pad_us"
PROC     = f"{BASE}/11_processed_layers"
RAST     = f"{PROC}/rasters"
TMP      = "/tmp/padus41_work"
TE       = "-2295000 310000 1791000 2907000"
STATES   = ["AZ", "IL", "IA", "OR", "TX", "VA", "WV"]

os.environ["PROJ_LIB"]  = "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj"
os.environ["GDAL_DATA"] = "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"

os.makedirs(TMP, exist_ok=True)
os.makedirs(RAST, exist_ok=True)

def run(cmd, check=True, capture=True):
    r = subprocess.run(cmd, capture_output=capture, text=True,
                       shell=isinstance(cmd, str))
    if check and r.returncode != 0 and capture:
        print(f"  WARN: {r.stderr[:300]}")
    return r

print("=== Step 1: PAD-US 4.1 Processing ===")
print("Source: USGS GAP Analysis Project PAD-US 4.1")
print("ScienceBase: https://www.sciencebase.gov/catalog/item/6759abcfd34edfeb8710a004")
print()

# ─── A. Verify input ZIPs ─────────────────────────────────────────────────────
print("--- A: Verifying input ZIPs ---")
missing = []
for state in STATES:
    zf = f"{PAD_RAW}/PADUS4_1_State_{state}_GDB_KMZ.zip"
    if os.path.exists(zf) and os.path.getsize(zf) > 1_000_000:
        sz_mb = os.path.getsize(zf) / 1024 / 1024
        print(f"  ✅ {state}: {sz_mb:.0f} MB")
    else:
        print(f"  ❌ {state}: MISSING — {zf}")
        missing.append(state)

if missing:
    print(f"\nERROR: {len(missing)} state(s) missing: {missing}")
    print("Please download the missing state ZIPs from:")
    print("  https://sciencebase.usgs.gov/manager/item/6759abcfd34edfeb8710a004")
    print("Files expected (GDB+KMZ ZIPs):")
    for st in missing:
        print(f"  PADUS4_1_State_{st}_GDB_KMZ.zip → {PAD_RAW}/")
    sys.exit(1)

# ─── B. Unzip ─────────────────────────────────────────────────────────────────
print("\n--- B: Unzipping state GDB+KMZ ZIPs ---")
for state in STATES:
    zf = f"{PAD_RAW}/PADUS4_1_State_{state}_GDB_KMZ.zip"
    out_dir = f"{TMP}/pad_{state}"
    if not os.path.isdir(out_dir):
        print(f"  Unzipping {state}...")
        subprocess.run(["unzip", "-q", zf, "-d", out_dir], check=True)
    else:
        print(f"  {state}: already unzipped")

# Find GDB directories
gdb_dirs = sorted([str(g) for g in Path(TMP).glob("**/*.gdb") if g.is_dir()])
print(f"\n  Found {len(gdb_dirs)} GDB directories:")
for g in gdb_dirs:
    print(f"    {g}")

if not gdb_dirs:
    print("ERROR: No GDB directories found")
    sys.exit(1)

# ─── C. Identify combined layer ───────────────────────────────────────────────
print("\n--- C: Identifying combined layer and GAP_Sts values ---")
sample_gdb = gdb_dirs[0]
r = run([f"{GDAL}/ogrinfo", sample_gdb])
layers = []
for line in r.stdout.split("\n"):
    if "Comb" in line:
        name = line.strip().split(": ", 1)[-1].split(" (")[0]
        layers.append(name)

if layers:
    print(f"  Combined layer template: {layers[0]}")
    # Extract state abbreviation pattern — should be PADUS4_1Comb_..._State_{ABBR}
else:
    print(f"  ERROR: No 'Comb' layer found in {sample_gdb}")
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

# ─── D. Merge GAP 1+2 across all states ──────────────────────────────────────
print("\n--- D: Merging GAP Status 1+2 (hard exclusion) ---")
GAP12_GPKG = f"{PROC}/pad_us_41_gap12_EPSG5070.gpkg"
if os.path.exists(GAP12_GPKG):
    os.remove(GAP12_GPKG)

for i, gdb in enumerate(gdb_dirs):
    gdb_name = Path(gdb).name   # e.g. PADUS4_1_StateAZ.gdb  OR  PADUS4_1_State_AZ.gdb
    # Try to extract state abbreviation robustly
    import re
    m = re.search(r'_State_?([A-Z]{2})\.gdb', gdb_name)
    if not m:
        m = re.search(r'pad_([A-Z]{2})/', gdb)  # fallback: from extract dir
    state_abb = m.group(1) if m else Path(gdb).parent.name.replace("pad_", "")

    # Build layer name — try 4.1 format first, fall back to discovered name
    layer = f"PADUS4_1Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_{state_abb}"
    # Verify layer exists; if not, discover from ogrinfo
    r_chk = run([f"{GDAL}/ogrinfo", gdb])
    found = [l.strip().split(": ",1)[-1].split(" (")[0]
             for l in r_chk.stdout.split("\n") if "Comb" in l]
    if found:
        layer = found[0]  # use discovered name (handles minor naming variations)
    print(f"  {state_abb} ({i+1}/{len(gdb_dirs)}): {layer}")

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

# Save raw copy
shutil.copy2(GAP12_GPKG, f"{PAD_RAW}/pad_us_41_gap12_EPSG5070.gpkg")

# ─── E. Rasterize GAP 1+2 ────────────────────────────────────────────────────
print("\n--- E: Rasterizing GAP 1+2 → 1km binary raster ---")
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

# ─── F. Merge GAP 3 ──────────────────────────────────────────────────────────
print("\n--- F: Merging GAP Status 3 (planning-review flag) ---")
GAP3_GPKG = f"{PROC}/pad_us_41_gap3_EPSG5070.gpkg"
if os.path.exists(GAP3_GPKG):
    os.remove(GAP3_GPKG)

for i, gdb in enumerate(gdb_dirs):
    gdb_name = Path(gdb).name
    m = re.search(r'_State_?([A-Z]{2})\.gdb', gdb_name)
    if not m:
        m = re.search(r'pad_([A-Z]{2})/', gdb)
    state_abb = m.group(1) if m else Path(gdb).parent.name.replace("pad_", "")

    r_chk = run([f"{GDAL}/ogrinfo", gdb])
    found = [l.strip().split(": ",1)[-1].split(" (")[0]
             for l in r_chk.stdout.split("\n") if "Comb" in l]
    layer = found[0] if found else f"PADUS4_1Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_{state_abb}"

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
shutil.copy2(GAP3_GPKG, f"{PAD_RAW}/pad_us_41_gap3_EPSG5070.gpkg")

# ─── G. Rasterize GAP 3 ──────────────────────────────────────────────────────
print("\n--- G: Rasterizing GAP 3 → 1km flag raster ---")
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

# ─── H. Known-place QC checks ─────────────────────────────────────────────────
print("\n--- H: QC — known protected area checks ---")
checks = [
    (-112.1, 36.1, "Grand Canyon NP      AZ", 1),
    (-88.8,  37.5, "Shawnee NF           IL", 1),
    (-78.4,  38.5, "Shenandoah NP        VA", 1),
    (-122.1, 42.9, "Crater Lake NP       OR", 1),
    (-79.8,  38.5, "Monongahela NF       WV", 1),   # may be GAP3 — check both
    (-93.6,  41.6, "Des Moines IA urban  IA", 0),
]
for lon, lat, name, expected in checks:
    r = run([f"{GDAL}/gdallocationinfo", "-wgs84", OUT12, str(lon), str(lat)])
    val = None
    for line in r.stdout.split("\n"):
        if "Value" in line:
            val = line.strip().split(":")[-1].strip()
    ok = "✅" if val == str(expected) else "⚠️ CHECK"
    print(f"  {ok} {name} ({lon},{lat}): got={val}, expected={expected}")

# Also check Monongahela in GAP3 raster
r = run([f"{GDAL}/gdallocationinfo", "-wgs84", OUT3, "-79.8", "38.5"])
val3 = None
for line in r.stdout.split("\n"):
    if "Value" in line:
        val3 = line.strip().split(":")[-1].strip()
print(f"  ℹ️  Monongahela NF in GAP3 raster: {val3} (expect 1 if GAP Status 3 in 4.1)")

# ─── I. Distribution stats ────────────────────────────────────────────────────
print("\n--- I: Distribution stats within 7-state mask ---")
try:
    from osgeo import gdal
    gdal.UseExceptions()
    mask_arr = gdal.Open(f"{RAST}/mask_7states_1km_EPSG5070.tif").GetRasterBand(1).ReadAsArray()
    n_mask = int((mask_arr == 1).sum())
    print(f"  Mask valid cells: {n_mask:,}")

    for path, label in [(OUT12, "GAP 1+2 hard-exclusion"), (OUT3, "GAP 3 flag")]:
        ds = gdal.Open(path)
        arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        nd  = ds.GetRasterBand(1).GetNoDataValue()
        valid = arr[(mask_arr == 1) & ((arr != nd) if nd is not None else True)]
        n_excl = int((valid == 1).sum())
        pct    = 100.0 * n_excl / n_mask
        print(f"  {label}: {n_excl:,} cells = {pct:.2f}% of study area")

    # Per-state feature counts
    from osgeo import ogr
    print()
    for gpkg, label in [(GAP12_GPKG, "GAP 1+2"), (GAP3_GPKG, "GAP 3")]:
        ds2 = ogr.Open(gpkg)
        lyr = ds2.GetLayer(0)
        total = lyr.GetFeatureCount()
        print(f"  {label} — Total: {total:,}")
        for state in STATES:
            lyr.SetAttributeFilter(f"State_Nm = '{state}'")
            print(f"    {state}: {lyr.GetFeatureCount():,}")
        lyr.SetAttributeFilter(None)
except Exception as e:
    print(f"  Stats error: {e}")

print(f"\n=== Step 1 PAD-US 4.1 COMPLETE: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
print("\nOutputs (all in project directory):")
for f in [OUT12, OUT3, GAP12_GPKG, GAP3_GPKG]:
    if os.path.exists(f):
        sz = os.path.getsize(f) / 1024 / 1024
        print(f"  {f}  ({sz:.1f} MB)")

print("\n✅ VERSION: PAD-US 4.1")
print("   Update all methodology text, dissertation, and admin docs to say PAD-US 4.1")
print("\nNext: run step1b_padus41_update_docs.sh to update readiness matrix and QGIS project")
