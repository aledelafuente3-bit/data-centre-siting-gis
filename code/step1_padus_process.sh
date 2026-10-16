#!/bin/bash
# Step 1: PAD-US 4.0 Processing — GAP 1+2 exclusion + GAP 3 flag rasters
#
# VERSION: PAD-US 4.0 (NOT 4.1 — ScienceBase item 652d4f80d34e44db0e2ee45c)
# Layer: PADUS4_0Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_{ABBR}
# Note: .gdb files are DIRECTORIES in the filesystem — use find -type d, not ls *.gdb
#
set -e

GDAL="/Applications/QGIS-LTR.app/Contents/MacOS/bin"
BASE="/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
PAD_RAW="${BASE}/08_protected_areas_and_land_cover/raw/pad_us"
PROC="${BASE}/11_processed_layers"
RAST="${PROC}/rasters"
TMP="/tmp/padus_work"
TE="-2295000 310000 1791000 2907000"

mkdir -p "$TMP" "$RAST"
echo "=== Step 1: PAD-US 4.0 Processing ==="
echo "Source: USGS GAP Analysis Project PAD-US 4.0"
echo "ScienceBase: https://www.sciencebase.gov/catalog/item/652d4f80d34e44db0e2ee45c"
echo ""

# ─── A. Unzip state GDB ZIPs ──────────────────────────────────────────────────
echo "--- A: Unzipping ---"
STATE_ZIPS=$(ls "${PAD_RAW}"/PADUS4_0_State_*_GDB.zip 2>/dev/null | wc -l | tr -d ' ')
echo "  Found $STATE_ZIPS state ZIP files"

for zip in "${PAD_RAW}"/PADUS4_0_State_*_GDB.zip; do
    state=$(basename "$zip" | sed 's/PADUS4_0_State_//;s/_GDB.zip//')
    out_dir="${TMP}/pad_${state}"
    if [ ! -d "$out_dir" ]; then
        echo "  Unzipping $state..."
        unzip -q "$zip" -d "$out_dir"
    else
        echo "  $state already unzipped"
    fi
done

# Find GDB directories using find -type d (GDBs are directories, not files)
mapfile -t GDB_DIRS < <(find "$TMP" -name "*.gdb" -type d | sort)
echo "  Found ${#GDB_DIRS[@]} GDB directories"
FIRST_GDB="${GDB_DIRS[0]}"
echo "  Sample GDB: $FIRST_GDB"

# List layers in sample GDB
echo "  Layers in sample GDB:"
"$GDAL/ogrinfo" "$FIRST_GDB" 2>/dev/null | grep "^[0-9]"

# ─── B. Identify combined layer and check GAP_Sts values ─────────────────────
echo ""
echo "--- B: Identifying combined layer and GAP_Sts values ---"
# The combined layer name for PAD-US 4.0 state GDBs:
# PADUS4_0Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_{ABBR}
# Use Python for robust layer name extraction
SAMPLE_LAYER=$("$GDAL/ogrinfo" "$FIRST_GDB" 2>/dev/null \
    | grep "Comb" | head -1 | sed 's/^[0-9]*: //' | sed 's/ (.*//')
echo "  Combined layer name: ${SAMPLE_LAYER}"

# Check GAP_Sts values
echo "  GAP_Sts values present:"
"$GDAL/ogrinfo" "$FIRST_GDB" -sql \
    "SELECT DISTINCT GAP_Sts FROM \"${SAMPLE_LAYER}\" ORDER BY GAP_Sts" \
    2>/dev/null | grep "GAP_Sts"

# ─── C. Merge GAP 1+2 across all states → GPKG ────────────────────────────────
echo ""
echo "--- C: Extracting and merging GAP Status 1+2 (hard exclusion) ---"
GAP12_GPKG="${PROC}/pad_us_40_gap12_EPSG5070.gpkg"
[ -f "$GAP12_GPKG" ] && rm "$GAP12_GPKG"
FIRST=1

for gdb in "${GDB_DIRS[@]}"; do
    # Extract state abbreviation from the GDB path
    STATE_ABB=$(basename "$gdb" | grep -oE "_State[A-Z]+" | sed 's/_State//')
    if [ -z "$STATE_ABB" ]; then
        STATE_ABB=$(basename "$(dirname "$gdb")" | sed 's/pad_//')
    fi
    # Construct combined layer name for this state
    LAYER="PADUS4_0Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_${STATE_ABB}"
    echo -n "  ${STATE_ABB}: "
    if [ $FIRST -eq 1 ]; then
        "$GDAL/ogr2ogr" -f "GPKG" -t_srs "EPSG:5070" \
          -where "GAP_Sts IN ('1','2')" \
          -nln "padus_gap12" \
          "$GAP12_GPKG" "$gdb" "$LAYER" 2>&1 | grep -v "^$" | head -2
        FIRST=0
    else
        "$GDAL/ogr2ogr" -f "GPKG" -t_srs "EPSG:5070" \
          -where "GAP_Sts IN ('1','2')" \
          -nln "padus_gap12" -append -update \
          "$GAP12_GPKG" "$gdb" "$LAYER" 2>&1 | grep -v "^$" | head -2
    fi
    FC=$("$GDAL/ogrinfo" -al -so "$GAP12_GPKG" 2>/dev/null | grep "Feature Count" | awk '{print $NF}')
    echo "  running total GAP1+2 features: $FC"
done

echo ""
FC12=$("$GDAL/ogrinfo" -al -so "$GAP12_GPKG" 2>/dev/null | grep "Feature Count" | awk '{print $NF}')
echo "  Total GAP 1+2 features: $FC12"
cp "$GAP12_GPKG" "${PAD_RAW}/pad_us_40_gap12_EPSG5070.gpkg"

# ─── D. Rasterize GAP 1+2 → binary 1km exclusion raster ─────────────────────
echo ""
echo "--- D: Rasterizing GAP 1+2 → 1km binary exclusion raster ---"
"$GDAL/gdal_rasterize" \
  -burn 1 -init 0 \
  -ot Byte -a_nodata 255 \
  -te $TE -tr 1000 1000 \
  -co "COMPRESS=LZW" \
  "$GAP12_GPKG" \
  "${RAST}/pad_us_gap12_exclusion_1km.tif" 2>&1 | tail -2
"$GDAL/gdalinfo" "${RAST}/pad_us_gap12_exclusion_1km.tif" 2>/dev/null \
    | grep -E "EPSG|Pixel Size|NoData|Min/Max"

# ─── E. Merge GAP 3 across all states → GPKG ─────────────────────────────────
echo ""
echo "--- E: Extracting and merging GAP Status 3 (planning-review flag) ---"
GAP3_GPKG="${PROC}/pad_us_40_gap3_EPSG5070.gpkg"
[ -f "$GAP3_GPKG" ] && rm "$GAP3_GPKG"
FIRST=1

for gdb in "${GDB_DIRS[@]}"; do
    STATE_ABB=$(basename "$gdb" | grep -oE "_State[A-Z]+" | sed 's/_State//')
    if [ -z "$STATE_ABB" ]; then
        STATE_ABB=$(basename "$(dirname "$gdb")" | sed 's/pad_//')
    fi
    LAYER="PADUS4_0Comb_DOD_Trib_NGP_Fee_Desig_Ease_State_${STATE_ABB}"
    echo -n "  ${STATE_ABB} GAP3: "
    if [ $FIRST -eq 1 ]; then
        "$GDAL/ogr2ogr" -f "GPKG" -t_srs "EPSG:5070" \
          -where "GAP_Sts = '3'" -nln "padus_gap3" \
          "$GAP3_GPKG" "$gdb" "$LAYER" 2>&1 | grep -v "^$" | head -1
        FIRST=0
    else
        "$GDAL/ogr2ogr" -f "GPKG" -t_srs "EPSG:5070" \
          -where "GAP_Sts = '3'" -nln "padus_gap3" -append -update \
          "$GAP3_GPKG" "$gdb" "$LAYER" 2>&1 | grep -v "^$" | head -1
    fi
    FC=$("$GDAL/ogrinfo" -al -so "$GAP3_GPKG" 2>/dev/null | grep "Feature Count" | awk '{print $NF}')
    echo "  running total GAP3 features: $FC"
done

FC3=$("$GDAL/ogrinfo" -al -so "$GAP3_GPKG" 2>/dev/null | grep "Feature Count" | awk '{print $NF}')
echo "  Total GAP 3 features: $FC3"
cp "$GAP3_GPKG" "${PAD_RAW}/pad_us_40_gap3_EPSG5070.gpkg"

# ─── F. Rasterize GAP 3 → flag raster ────────────────────────────────────────
echo ""
echo "--- F: Rasterizing GAP 3 → 1km flag raster ---"
"$GDAL/gdal_rasterize" \
  -burn 1 -init 0 \
  -ot Byte -a_nodata 255 \
  -te $TE -tr 1000 1000 \
  -co "COMPRESS=LZW" \
  "$GAP3_GPKG" \
  "${RAST}/pad_us_gap3_flag_1km.tif" 2>&1 | tail -2
"$GDAL/gdalinfo" "${RAST}/pad_us_gap3_flag_1km.tif" 2>/dev/null \
    | grep -E "EPSG|Pixel Size|NoData|Min/Max"

# ─── G. QC checks ─────────────────────────────────────────────────────────────
echo ""
echo "--- G: QC known-place checks ---"
echo -n "  Grand Canyon NP    (AZ -112.1,36.1, expect=1): "
"$GDAL/gdallocationinfo" -wgs84 "${RAST}/pad_us_gap12_exclusion_1km.tif" -112.1 36.1 2>/dev/null \
    | grep "Value" | tr -d '\n'; echo ""
echo -n "  Shawnee NF         (IL -88.8,37.5,  expect=1): "
"$GDAL/gdallocationinfo" -wgs84 "${RAST}/pad_us_gap12_exclusion_1km.tif" -88.8 37.5 2>/dev/null \
    | grep "Value" | tr -d '\n'; echo ""
echo -n "  Shenandoah NP      (VA -78.4,38.5,  expect=1): "
"$GDAL/gdallocationinfo" -wgs84 "${RAST}/pad_us_gap12_exclusion_1km.tif" -78.4 38.5 2>/dev/null \
    | grep "Value" | tr -d '\n'; echo ""
echo -n "  Crater Lake NP     (OR -122.1,42.9, expect=1): "
"$GDAL/gdallocationinfo" -wgs84 "${RAST}/pad_us_gap12_exclusion_1km.tif" -122.1 42.9 2>/dev/null \
    | grep "Value" | tr -d '\n'; echo ""
echo -n "  Monongahela NF     (WV -79.8,38.5,  expect=1): "
"$GDAL/gdallocationinfo" -wgs84 "${RAST}/pad_us_gap12_exclusion_1km.tif" -79.8 38.5 2>/dev/null \
    | grep "Value" | tr -d '\n'; echo ""
echo -n "  Des Moines IA urban(IA -93.6,41.6,  expect=0): "
"$GDAL/gdallocationinfo" -wgs84 "${RAST}/pad_us_gap12_exclusion_1km.tif" -93.6 41.6 2>/dev/null \
    | grep "Value" | tr -d '\n'; echo ""

# ─── H. Distribution stats ────────────────────────────────────────────────────
echo ""
echo "--- H: Distribution stats within 7-state mask ---"
"$GDAL/python3" << 'PYEOF'
import numpy as np, os
from osgeo import gdal
gdal.UseExceptions()
RAST = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/11_processed_layers/rasters"
mask_arr = gdal.Open(f"{RAST}/mask_7states_1km_EPSG5070.tif").GetRasterBand(1).ReadAsArray()
n_mask = int((mask_arr == 1).sum())
print(f"  Mask valid cells: {n_mask:,}")
for name, label in [
    ("pad_us_gap12_exclusion_1km", "GAP 1+2 hard-exclusion"),
    ("pad_us_gap3_flag_1km",       "GAP 3 planning-review flag"),
]:
    path = f"{RAST}/{name}.tif"
    if not os.path.exists(path):
        print(f"  {name}: NOT FOUND"); continue
    ds = gdal.Open(path)
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    nd = ds.GetRasterBand(1).GetNoDataValue()
    valid = arr[(mask_arr == 1) & ((arr != nd) if nd is not None else True)]
    n_excl = int((valid == 1).sum())
    pct = 100.0 * n_excl / n_mask
    print(f"  {label}: {n_excl:,} cells = {pct:.2f}% of study area")
    # CRS check
    proj = ds.GetProjection()
    epsg = "EPSG:5070" if "5070" in proj else "CHECK"
    gt = ds.GetGeoTransform()
    print(f"    CRS: {epsg} | Pixel: {abs(gt[1]):.0f}m | NoData: {nd}")
PYEOF

echo ""
echo "=== Step 1 PAD-US 4.0 COMPLETE: $(date) ==="
echo ""
echo "Outputs (no /tmp references — all in project dir):"
ls -lh "${RAST}/pad_us_gap12_exclusion_1km.tif" "${RAST}/pad_us_gap3_flag_1km.tif" 2>/dev/null
ls -lh "${PROC}/pad_us_40_gap12_EPSG5070.gpkg" "${PROC}/pad_us_40_gap3_EPSG5070.gpkg" 2>/dev/null
echo ""
echo "Source copies preserved:"
ls -lh "${PAD_RAW}"/*.zip 2>/dev/null | head -10
echo ""
echo "VERSION: PAD-US 4.0 (NOT 4.1)"
echo "Update all methodology notes, dissertation text, and output names to say PAD-US 4.0"
