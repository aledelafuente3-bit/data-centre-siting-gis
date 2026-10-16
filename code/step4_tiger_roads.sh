#!/bin/bash
# Step 4: TIGER 2025 Roads — Primary and Primary+Secondary proximity rasters
set -e

GDAL="/Applications/QGIS-LTR.app/Contents/MacOS/bin"
BASE="/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
ROADS_DIR="${BASE}/01_RAW_DATA/infrastructure/roads/raw"
PROC="${BASE}/11_processed_layers"
RAST="${PROC}/rasters"
MASK="${RAST}/mask_7states_1km_EPSG5070.tif"
TE="-2295000 310000 1791000 2907000"
TR="-tr 1000 1000"
CRS="EPSG:5070"
NODATA="-9999"
TMP="/tmp/tiger_roads_work"

mkdir -p "$TMP"
echo "=== Step 4: TIGER 2025 Roads Processing ==="
echo "Temp dir: $TMP"

# ─── A. Reproject and merge primary roads (S1100 from national file) ──────────
echo ""
echo "--- A: Primary roads (S1100) ---"

$GDAL/ogr2ogr -f "GPKG" -t_srs $CRS \
  -where "MTFCC = 'S1100'" \
  -clipdst $TE \
  "${TMP}/primary_s1100_EPSG5070.gpkg" \
  "${ROADS_DIR}/tl_2025_us_primaryroads/tl_2025_us_primaryroads.shp"

echo "Primary roads features:"
$GDAL/ogrinfo -al -so "${TMP}/primary_s1100_EPSG5070.gpkg" 2>/dev/null | grep "Feature Count"

# Save final primary GPKG
cp "${TMP}/primary_s1100_EPSG5070.gpkg" \
   "${PROC}/tiger_primary_roads_7states_EPSG5070.gpkg"
echo "Saved: tiger_primary_roads_7states_EPSG5070.gpkg"

# ─── B. Merge prisecroads (S1100+S1200 from all 7 states) ────────────────────
echo ""
echo "--- B: Primary + Secondary roads (S1100+S1200) ---"

# Create merged GPKG from all 7-state prisecroads files
FIRST=1
for fip in 04 17 19 41 48 51 54; do
  SHP="${ROADS_DIR}/tl_2025_${fip}_prisecroads/tl_2025_${fip}_prisecroads.shp"
  echo "  Processing FIPS ${fip}..."
  
  if [ $FIRST -eq 1 ]; then
    $GDAL/ogr2ogr -f "GPKG" -t_srs $CRS \
      -where "MTFCC IN ('S1100','S1200')" \
      "${TMP}/prisec_all_EPSG5070.gpkg" "$SHP"
    FIRST=0
  else
    $GDAL/ogr2ogr -f "GPKG" -t_srs $CRS \
      -where "MTFCC IN ('S1100','S1200')" \
      -append \
      "${TMP}/prisec_all_EPSG5070.gpkg" "$SHP"
  fi
done

echo "Primary+Secondary features:"
$GDAL/ogrinfo -al -so "${TMP}/prisec_all_EPSG5070.gpkg" 2>/dev/null | grep "Feature Count"

# Save final prisec GPKG
cp "${TMP}/prisec_all_EPSG5070.gpkg" \
   "${PROC}/tiger_prisec_roads_7states_EPSG5070.gpkg"
echo "Saved: tiger_prisec_roads_7states_EPSG5070.gpkg"

# ─── C. Rasterize primary roads to binary burn at 1km ────────────────────────
echo ""
echo "--- C: Rasterizing primary roads ---"

$GDAL/gdal_rasterize \
  -burn 1 -init 0 \
  -ot Byte -a_nodata 255 \
  -te $TE -tr 1000 1000 \
  -co "COMPRESS=LZW" \
  "${TMP}/primary_s1100_EPSG5070.gpkg" \
  "${TMP}/primary_burn_1km.tif"
echo "Primary burn done"

# ─── D. Rasterize primary+secondary roads ────────────────────────────────────
echo ""
echo "--- D: Rasterizing primary+secondary roads ---"

$GDAL/gdal_rasterize \
  -burn 1 -init 0 \
  -ot Byte -a_nodata 255 \
  -te $TE -tr 1000 1000 \
  -co "COMPRESS=LZW" \
  "${TMP}/prisec_all_EPSG5070.gpkg" \
  "${TMP}/prisec_burn_1km.tif"
echo "PriSec burn done"

# ─── E. Compute proximity for primary roads ───────────────────────────────────
echo ""
echo "--- E: gdal_proximity primary roads ---"

$GDAL/gdal_proximity.py \
  "${TMP}/primary_burn_1km.tif" \
  "${TMP}/primary_prox_raw.tif" \
  -values 1 -distunits GEO -maxdist 400000 \
  -nodata -9999 -ot Float32 2>/dev/null

# Mask to study area
$GDAL/gdal_calc.py \
  -A "${TMP}/primary_prox_raw.tif" \
  -B "$MASK" \
  --outfile="${RAST}/tiger_roads_primary_proximity_1km.tif" \
  --calc="numpy.where(B==1, A, -9999)" \
  --NoDataValue=-9999 --type=Float32 \
  --co="COMPRESS=LZW" --quiet

echo "Primary proximity done"
$GDAL/gdalinfo -mm "${RAST}/tiger_roads_primary_proximity_1km.tif" 2>/dev/null | grep -E "Min/Max|NoData"

# ─── F. Compute proximity for primary+secondary roads ─────────────────────────
echo ""
echo "--- F: gdal_proximity primary+secondary roads ---"

$GDAL/gdal_proximity.py \
  "${TMP}/prisec_burn_1km.tif" \
  "${TMP}/prisec_prox_raw.tif" \
  -values 1 -distunits GEO -maxdist 400000 \
  -nodata -9999 -ot Float32 2>/dev/null

$GDAL/gdal_calc.py \
  -A "${TMP}/prisec_prox_raw.tif" \
  -B "$MASK" \
  --outfile="${RAST}/tiger_roads_prisec_proximity_1km.tif" \
  --calc="numpy.where(B==1, A, -9999)" \
  --NoDataValue=-9999 --type=Float32 \
  --co="COMPRESS=LZW" --quiet

echo "PriSec proximity done"
$GDAL/gdalinfo -mm "${RAST}/tiger_roads_prisec_proximity_1km.tif" 2>/dev/null | grep -E "Min/Max|NoData"

# ─── G. QC ───────────────────────────────────────────────────────────────────
echo ""
echo "=== QC ==="
for f in tiger_roads_primary_proximity_1km.tif tiger_roads_prisec_proximity_1km.tif; do
  echo "--- $f ---"
  $GDAL/gdalinfo -stats "${RAST}/$f" 2>/dev/null | grep -E "STATISTICS_MIN|STATISTICS_MAX|STATISTICS_MEAN|Size is"
done

echo ""
echo "=== Step 4 COMPLETE ==="
echo "Outputs:"
ls -lh "${PROC}/tiger_primary_roads_7states_EPSG5070.gpkg" \
        "${PROC}/tiger_prisec_roads_7states_EPSG5070.gpkg" \
        "${RAST}/tiger_roads_primary_proximity_1km.tif" \
        "${RAST}/tiger_roads_prisec_proximity_1km.tif"
