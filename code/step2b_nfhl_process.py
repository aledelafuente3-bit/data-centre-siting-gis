#!/usr/bin/env python3
"""
Step 2b: Process NFHL GeoJSON downloads → GPKG → 4 rasters
  1. nfhl_sfha_exclusion_1km.tif   — binary 0/1
  2. nfhl_sfha_fraction_1km.tif    — fractional (0–1) from 100m intermediate
  3. nfhl_floodway_fraction_1km.tif — floodway fraction
  4. nfhl_coverage_qa_1km.tif      — mapped/unmapped (1=mapped, 0=unmapped)
"""
import os, subprocess, glob

os.environ['PROJ_LIB']  = '/Applications/QGIS-LTR.app/Contents/Resources/proj'
os.environ['PROJ_DATA'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj'

BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
NFHL_DIR = f"{BASE}/07_hazards/raw/flood/nfhl"
PROC     = f"{BASE}/11_processed_layers"
RAST     = f"{PROC}/rasters"
GDAL     = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
TMP      = "/tmp/nfhl_work"

os.makedirs(TMP, exist_ok=True)

# Grid parameters
TE  = "-2295000 310000 1791000 2907000"
TR1 = "-tr 1000 1000"
TR100 = "-tr 100 100"
MASK = f"{RAST}/mask_7states_1km_EPSG5070.tif"

def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=isinstance(cmd, str))
    if check and result.returncode != 0:
        print(f"ERROR: {result.stderr[:300]}")
    return result

print("=== Step 2b: NFHL Processing ===")

# ─── A. Merge SFHA GeoJSONs → single GPKG ─────────────────────────────────────
print("\n--- A: Merging SFHA GeoJSONs → GPKG ---")
sfha_jsons = sorted(glob.glob(f"{NFHL_DIR}/nfhl_sfha_*.geojson"))
print(f"  Found {len(sfha_jsons)} state files")

SFHA_GPKG = f"{PROC}/nfhl_sfha_7states_EPSG5070.gpkg"
if os.path.exists(SFHA_GPKG):
    os.remove(SFHA_GPKG)

first = True
for j in sfha_jsons:
    state = os.path.basename(j).split('_')[-1].replace('.geojson','').upper()
    print(f"  Merging {state}...")
    if first:
        run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:5070",
             "-nlt", "MULTIPOLYGON", "-nln", "nfhl_sfha",
             SFHA_GPKG, j])
        first = False
    else:
        run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:5070",
             "-nlt", "MULTIPOLYGON", "-nln", "nfhl_sfha", "-append", "-update",
             SFHA_GPKG, j])

r = subprocess.run([f"{GDAL}/ogrinfo", "-al", "-so", SFHA_GPKG],
                   capture_output=True, text=True)
for line in r.stdout.split('\n'):
    if 'Feature Count' in line or 'Extent' in line:
        print(f"  {line.strip()}")

# ─── B. Merge Availability GeoJSONs → GPKG ────────────────────────────────────
print("\n--- B: Merging Availability GeoJSONs → GPKG ---")
avail_jsons = sorted(glob.glob(f"{NFHL_DIR}/nfhl_avail_*.geojson"))
print(f"  Found {len(avail_jsons)} state files")

AVAIL_GPKG = f"{PROC}/nfhl_availability_7states_EPSG5070.gpkg"
if os.path.exists(AVAIL_GPKG) and avail_jsons:
    os.remove(AVAIL_GPKG)

first = True
for j in avail_jsons:
    state = os.path.basename(j).split('_')[-1].replace('.geojson','').upper()
    print(f"  Merging {state}...")
    if first:
        run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:5070",
             "-nlt", "MULTIPOLYGON", "-nln", "nfhl_avail",
             AVAIL_GPKG, j])
        first = False
    else:
        run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-t_srs", "EPSG:5070",
             "-nlt", "MULTIPOLYGON", "-nln", "nfhl_avail", "-append", "-update",
             AVAIL_GPKG, j])

# ─── C. Binary SFHA exclusion raster at 1km ───────────────────────────────────
print("\n--- C: SFHA binary exclusion raster (1km) ---")
run([f"{GDAL}/gdal_rasterize",
     "-burn", "1", "-init", "0", "-ot", "Byte", "-a_nodata", "255",
     "-te"] + TE.split() + ["-tr", "1000", "1000", "-co", "COMPRESS=LZW",
     SFHA_GPKG, f"{RAST}/nfhl_sfha_exclusion_1km.tif"])
r = subprocess.run([f"{GDAL}/gdalinfo", "-mm", f"{RAST}/nfhl_sfha_exclusion_1km.tif"],
                   capture_output=True, text=True)
for line in r.stdout.split('\n'):
    if 'Min/Max' in line: print(f"  {line.strip()}")

# ─── D. Fractional SFHA coverage: rasterize at 100m → aggregate to 1km ────────
print("\n--- D: SFHA fractional coverage (100m → 1km avg) ---")
SFHA_100 = f"{TMP}/sfha_100m.tif"
run([f"{GDAL}/gdal_rasterize",
     "-burn", "1", "-init", "0", "-ot", "Byte", "-a_nodata", "255",
     "-te"] + TE.split() + ["-tr", "100", "100",
     SFHA_GPKG, SFHA_100])

run([f"{GDAL}/gdalwarp",
     "-r", "average", "-tr", "1000", "1000",
     "-te"] + TE.split() + ["-co", "COMPRESS=LZW",
     SFHA_100, f"{RAST}/nfhl_sfha_fraction_1km.tif"])
r = subprocess.run([f"{GDAL}/gdalinfo", "-mm", f"{RAST}/nfhl_sfha_fraction_1km.tif"],
                   capture_output=True, text=True)
for line in r.stdout.split('\n'):
    if 'Min/Max' in line: print(f"  {line.strip()}")

# ─── E. Floodway fractional raster ────────────────────────────────────────────
print("\n--- E: Floodway fraction raster (100m → 1km) ---")
FLOODWAY_GPKG = f"{TMP}/nfhl_floodway.gpkg"

# Floodway = ZONE_SUBTY = 'FLOODWAY'
run([f"{GDAL}/ogr2ogr", "-f", "GPKG", "-where", "ZONE_SUBTY = 'FLOODWAY'",
     FLOODWAY_GPKG, SFHA_GPKG])

r2 = subprocess.run([f"{GDAL}/ogrinfo", "-al", "-so", FLOODWAY_GPKG],
                    capture_output=True, text=True)
for line in r2.stdout.split('\n'):
    if 'Feature Count' in line: print(f"  Floodway features: {line.strip()}")

FW_100 = f"{TMP}/floodway_100m.tif"
run([f"{GDAL}/gdal_rasterize",
     "-burn", "1", "-init", "0", "-ot", "Byte", "-a_nodata", "255",
     "-te"] + TE.split() + ["-tr", "100", "100",
     FLOODWAY_GPKG, FW_100])

run([f"{GDAL}/gdalwarp",
     "-r", "average", "-tr", "1000", "1000",
     "-te"] + TE.split() + ["-co", "COMPRESS=LZW",
     FW_100, f"{RAST}/nfhl_floodway_fraction_1km.tif"])
r = subprocess.run([f"{GDAL}/gdalinfo", "-mm", f"{RAST}/nfhl_floodway_fraction_1km.tif"],
                   capture_output=True, text=True)
for line in r.stdout.split('\n'):
    if 'Min/Max' in line: print(f"  {line.strip()}")

# ─── F. NFHL coverage QA flag: mapped areas ───────────────────────────────────
print("\n--- F: NFHL coverage QA raster ---")
if os.path.exists(AVAIL_GPKG):
    run([f"{GDAL}/gdal_rasterize",
         "-burn", "1", "-init", "0", "-ot", "Byte", "-a_nodata", "255",
         "-te"] + TE.split() + ["-tr", "1000", "1000", "-co", "COMPRESS=LZW",
         AVAIL_GPKG, f"{RAST}/nfhl_coverage_qa_1km.tif"])
    r = subprocess.run([f"{GDAL}/gdalinfo", "-mm", f"{RAST}/nfhl_coverage_qa_1km.tif"],
                       capture_output=True, text=True)
    for line in r.stdout.split('\n'):
        if 'Min/Max' in line: print(f"  {line.strip()}")
else:
    print("  No availability GeoJSONs found — coverage QA not generated")

# ─── G. Summary ───────────────────────────────────────────────────────────────
print("\n=== Step 2 NFHL Complete ===")
outputs = [
    'nfhl_sfha_exclusion_1km.tif',
    'nfhl_sfha_fraction_1km.tif',
    'nfhl_floodway_fraction_1km.tif',
    'nfhl_coverage_qa_1km.tif',
]
for f in outputs:
    path = f"{RAST}/{f}"
    if os.path.exists(path):
        print(f"  {f}: {os.path.getsize(path)/1024/1024:.1f} MB")
    else:
        print(f"  {f}: NOT GENERATED")
