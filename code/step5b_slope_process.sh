#!/bin/bash
# Step 5b: 3DEP DEM → mosaic → reproject → slope → 5 rasters at 1km
# Run AFTER step5_3dep_download.py completes
#
# RESOLUTION NOTE (disk-constraint fallback):
#   The primary plan specified 30m intermediate resolution.
#   At 30m, the reprojected DEM would be ~15–18 GB and disk space was insufficient.
#   This script uses 100m intermediate resolution instead:
#     - DEM @ 100m: ~4.25 GB (Float32) before LZW compression
#     - Slope @ 100m: ~4.25 GB (Float32) before LZW compression
#     - Binary masks @ 100m: ~0.5 GB each (Byte, LZW)
#     - Peak disk use: ~10 GB intermediates (within 18 GB available)
#   At 100m each 1km² output cell has 100 sub-pixels — fully adequate for
#   regional data-centre siting at 1 km resolution. The final 1km aggregates
#   (fraction below 3%, below 8%, above 15%, mean, max) are produced by
#   gdalwarp -r average / -r max over the 100m intermediate, which accurately
#   captures the within-cell slope distribution at the study scale.
#   Document in dissertation methods: "Slope rasters aggregated from
#   USGS 3DEP 1 arc-second DEM via 100m intermediate (100 sub-pixels/km²)
#   due to disk constraints during processing; resolution exceeds the
#   1 km suitability grid by 2 orders of magnitude."

set -e

GDAL="/Applications/QGIS-LTR.app/Contents/MacOS/bin"
BASE="/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
DEM_DIR="${BASE}/08_protected_areas_and_land_cover/raw/dem_3dep"
RAST="${BASE}/11_processed_layers/rasters"
MASK="${RAST}/mask_7states_1km_EPSG5070.tif"
TMP="/tmp/dem_work"
TE="-2295000 310000 1791000 2907000"

mkdir -p "$TMP"
echo "=== Step 5b: 3DEP Slope Processing (100m fallback) ==="
echo "Started: $(date)"

DEM_COUNT=$(ls "${DEM_DIR}"/USGS_1_*.tif 2>/dev/null | wc -l | tr -d ' ')
echo "DEM tiles available: $DEM_COUNT"

# ─── 1. Build virtual mosaic ──────────────────────────────────────────────────
echo ""
echo "--- 1: Building VRT mosaic ---"
$GDAL/gdalbuildvrt "${TMP}/dem_mosaic.vrt" "${DEM_DIR}"/USGS_1_*.tif
echo "Done"

# ─── 2. Reproject to EPSG:5070 at 100m ───────────────────────────────────────
echo ""
echo "--- 2: Reprojecting to EPSG:5070 at 100m (disk-constraint fallback) ---"
echo "Expected output size: ~4.25 GB (Float32, LZW)"
$GDAL/gdalwarp \
  -t_srs EPSG:5070 \
  -tr 100 100 \
  -r bilinear \
  -te $TE \
  -co COMPRESS=LZW \
  -co BIGTIFF=YES \
  "${TMP}/dem_mosaic.vrt" \
  "${TMP}/dem_100m_EPSG5070.tif" 2>&1 | tail -3
echo "Done: $(date)"
$GDAL/gdalinfo -mm "${TMP}/dem_100m_EPSG5070.tif" 2>/dev/null | grep "Min/Max"
ls -lh "${TMP}/dem_100m_EPSG5070.tif"
df -h /tmp | tail -1

# ─── 3. Compute slope in degrees ─────────────────────────────────────────────
echo ""
echo "--- 3: Computing slope (degrees) from 100m DEM ---"
$GDAL/gdaldem slope \
  "${TMP}/dem_100m_EPSG5070.tif" \
  "${TMP}/slope_100m.tif" \
  -compute_edges -co COMPRESS=LZW -co BIGTIFF=YES 2>&1 | tail -3
echo "Done: $(date)"
$GDAL/gdalinfo -mm "${TMP}/slope_100m.tif" 2>/dev/null | grep "Min/Max"
ls -lh "${TMP}/slope_100m.tif"
df -h /tmp | tail -1

# ─── 4. Create binary threshold masks at 100m ─────────────────────────────────
echo ""
echo "--- 4: Creating slope threshold masks (100m) ---"
# Percent-slope → degrees: 3% = 1.72°, 8% = 4.57°, 15% = 8.53°
PROJ_LIB=/Applications/QGIS-LTR.app/Contents/Resources/proj \
$GDAL/gdal_calc.py -A "${TMP}/slope_100m.tif" \
  --outfile="${TMP}/below172deg_100m.tif" \
  --calc="numpy.where(A<1.72, numpy.uint8(1), numpy.uint8(0))" \
  --type=Byte --NoDataValue=255 --co COMPRESS=LZW --quiet

PROJ_LIB=/Applications/QGIS-LTR.app/Contents/Resources/proj \
$GDAL/gdal_calc.py -A "${TMP}/slope_100m.tif" \
  --outfile="${TMP}/below457deg_100m.tif" \
  --calc="numpy.where(A<4.57, numpy.uint8(1), numpy.uint8(0))" \
  --type=Byte --NoDataValue=255 --co COMPRESS=LZW --quiet

PROJ_LIB=/Applications/QGIS-LTR.app/Contents/Resources/proj \
$GDAL/gdal_calc.py -A "${TMP}/slope_100m.tif" \
  --outfile="${TMP}/above853deg_100m.tif" \
  --calc="numpy.where(A>8.53, numpy.uint8(1), numpy.uint8(0))" \
  --type=Byte --NoDataValue=255 --co COMPRESS=LZW --quiet
echo "Done: $(date)"
ls -lh "${TMP}"/*.tif 2>/dev/null

# ─── 5. Aggregate to 1km rasters ─────────────────────────────────────────────
echo ""
echo "--- 5: Aggregating to 1km rasters ---"

echo "  5a. Fraction below 3% slope (<1.72°) ..."
$GDAL/gdalwarp -r average -tr 1000 1000 -te $TE -co COMPRESS=LZW \
  "${TMP}/below172deg_100m.tif" "${RAST}/slope_pct_below3pct_1km.tif"
$GDAL/gdalinfo -mm "${RAST}/slope_pct_below3pct_1km.tif" 2>/dev/null | grep "Min/Max"

echo "  5b. Fraction below 8% slope (<4.57°) ..."
$GDAL/gdalwarp -r average -tr 1000 1000 -te $TE -co COMPRESS=LZW \
  "${TMP}/below457deg_100m.tif" "${RAST}/slope_pct_below8pct_1km.tif"
$GDAL/gdalinfo -mm "${RAST}/slope_pct_below8pct_1km.tif" 2>/dev/null | grep "Min/Max"

echo "  5c. Fraction above 15% slope (>8.53°) ..."
$GDAL/gdalwarp -r average -tr 1000 1000 -te $TE -co COMPRESS=LZW \
  "${TMP}/above853deg_100m.tif" "${RAST}/slope_pct_above15pct_1km.tif"
$GDAL/gdalinfo -mm "${RAST}/slope_pct_above15pct_1km.tif" 2>/dev/null | grep "Min/Max"

echo "  5d. Mean slope (degrees) ..."
$GDAL/gdalwarp -r average -tr 1000 1000 -te $TE -co COMPRESS=LZW \
  "${TMP}/slope_100m.tif" "${RAST}/slope_mean_1km_EPSG5070.tif"
$GDAL/gdalinfo -mm "${RAST}/slope_mean_1km_EPSG5070.tif" 2>/dev/null | grep "Min/Max"

echo "  5e. Max slope (QC context only) ..."
$GDAL/gdalwarp -r max -tr 1000 1000 -te $TE -co COMPRESS=LZW \
  "${TMP}/slope_100m.tif" "${RAST}/slope_max_1km_EPSG5070.tif"
$GDAL/gdalinfo -mm "${RAST}/slope_max_1km_EPSG5070.tif" 2>/dev/null | grep "Min/Max"

# ─── 6. Distribution stats ───────────────────────────────────────────────────
echo ""
echo "--- 6: Distribution stats within 7-state mask ---"
/Applications/QGIS-LTR.app/Contents/MacOS/bin/python3 << 'PYEOF'
import numpy as np
import os
from osgeo import gdal
gdal.UseExceptions()

RAST = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/11_processed_layers/rasters"
MASK = f"{RAST}/mask_7states_1km_EPSG5070.tif"

mask_ds = gdal.Open(MASK)
mask_arr = mask_ds.GetRasterBand(1).ReadAsArray()

print("\nSlope distribution within 7-state mask (100m fallback intermediate):")
print(f"{'Layer':<35} {'P10':>8} {'P25':>8} {'P50':>8} {'P75':>8} {'P90':>8} {'Mean':>8}")
print("-" * 90)

layers = [
    'slope_pct_below8pct_1km',
    'slope_mean_1km_EPSG5070',
    'slope_pct_below3pct_1km',
    'slope_pct_above15pct_1km',
    'slope_max_1km_EPSG5070',
]

for name in layers:
    path = f"{RAST}/{name}.tif"
    if not os.path.exists(path):
        print(f"  {name}: NOT FOUND")
        continue
    ds = gdal.Open(path)
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    nd = ds.GetRasterBand(1).GetNoDataValue()
    if nd is not None:
        valid = arr[(mask_arr == 1) & (arr != nd) & (arr > -9990)]
    else:
        valid = arr[mask_arr == 1]
    if len(valid) == 0:
        print(f"  {name}: NO VALID CELLS")
        continue
    p = np.percentile(valid, [10, 25, 50, 75, 90])
    nodata_pct = 100.0 * (1 - len(valid) / (mask_arr == 1).sum())
    print(f"  {name:<35} {p[0]:>8.3f} {p[1]:>8.3f} {p[2]:>8.3f} {p[3]:>8.3f} {p[4]:>8.3f} {valid.mean():>8.3f}  (ND={nodata_pct:.1f}%)")
PYEOF

echo ""
echo "=== Step 5b 3DEP Slope COMPLETE: $(date) ==="
echo ""
echo "Final 1km slope rasters:"
ls -lh "${RAST}"/slope_*.tif 2>/dev/null
echo ""
echo "Intermediate files in /tmp/dem_work (safe to delete after QC):"
ls -lh "${TMP}"/*.tif 2>/dev/null
df -h /tmp | tail -1
