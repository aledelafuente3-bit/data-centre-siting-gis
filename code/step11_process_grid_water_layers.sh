#!/bin/bash
# Step 11 — Process supplementary grid availability and water scarcity layers
# Uses gis_venv Python for data prep, QGIS GDAL tools for rasterization

BASE="/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
GIS_PY="$BASE/13_scripts/gis_venv/bin/python3"
QGIS_PY="/Applications/QGIS-LTR.app/Contents/MacOS/bin/python3"
GDAL_BIN="/Applications/QGIS-LTR.app/Contents/MacOS/bin"
export PROJ_LIB="/Applications/QGIS-LTR.app/Contents/MacOS/share/proj"
export GDAL_DATA="/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"

RASTERS="$BASE/11_processed_layers/rasters"
TEMP="/tmp/step11"
MASK="$RASTERS/mask_7states_1km_EPSG5070.tif"
XMIN=-2295000; YMIN=310000; XMAX=1791000; YMAX=2907000
ND=-9999

mkdir -p "$TEMP"
cd "$BASE"

echo "============================================================"
echo "STEP 11 — Grid availability + water scarcity layers"
echo "============================================================"

# ────────────────────────────────────────────────────────────────
# STAGE A: gis_venv data preparation → intermediate GPKGs
# ────────────────────────────────────────────────────────────────
echo ""
echo "[A] Data preparation (gis_venv Python)"

$GIS_PY - << 'PYEOF'
import os, sys, zipfile
import numpy as np
import pandas as pd

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
TEMP = "/tmp/step11"
os.makedirs(TEMP, exist_ok=True)

STATES_7 = {"AZ","IL","IA","OR","TX","VA","WV"}
NAME_TO_ABBR = {
    "Arizona":"AZ","Illinois":"IL","Iowa":"IA",
    "Oregon":"OR","Texas":"TX","Virginia":"VA","West Virginia":"WV"
}

# ── A1: Aqueduct IAV + GTD: compute suitability scores ──────────
print("  [A1] Aqueduct IAV/GTD suitability fields")
try:
    from osgeo import ogr
    aq_gpkg = f"{TEMP}/aqueduct_extra.gpkg"
    ds = ogr.Open(aq_gpkg, 1)
    lyr = ds.GetLayer(0)   # layer is "baseline_annual"
    print(f"       Layer: {lyr.GetName()}, features: {lyr.GetFeatureCount()}")
    for field in ["iav_suit","gtd_suit"]:
        if lyr.GetLayerDefn().GetFieldIndex(field) == -1:
            lyr.CreateField(ogr.FieldDefn(field, ogr.OFTReal))
    lyr.ResetReading()
    lyr.StartTransaction()
    for feat in lyr:
        iav = feat.GetField("iav_score")
        gtd = feat.GetField("gtd_score")
        iav_s = max(0.0, 1.0 - (iav or 0)/5.0) if iav is not None and iav >= 0 else 1.0
        gtd_s = max(0.0, 1.0 - max(0.0, gtd)/5.0) if gtd is not None and gtd >= 0 else 1.0
        feat.SetField("iav_suit", round(iav_s, 4))
        feat.SetField("gtd_suit", round(gtd_s, 4))
        lyr.SetFeature(feat)
    lyr.CommitTransaction()
    ds = None
    print(f"       OK — IAV/GTD suitability fields written")
except Exception as e:
    print(f"       FAIL: {e}")

# ── A2: PDSI — already joined to shapefile in previous run ──────
print("  [A2] PDSI — re-verify shapefile has pdsi_suit")
try:
    from osgeo import ogr
    pdsi_shp = f"{BASE}/07_hazards/raw/drought/pdsi/GIS.OFFICIAL_CLIM_DIVISIONS.shp"
    ds = ogr.Open(pdsi_shp)
    lyr = ds.GetLayer(0)
    lyr.ResetReading()
    feat = lyr.GetNextFeature()
    has_suit = lyr.GetLayerDefn().GetFieldIndex("pdsi_suit") >= 0
    has_mean = lyr.GetLayerDefn().GetFieldIndex("pdsi_mean") >= 0
    print(f"       pdsi_suit field exists: {has_suit}")
    if has_suit and feat:
        print(f"       Sample pdsi_suit: {feat.GetField('pdsi_suit')}")
    ds = None
    if not has_suit:
        raise Exception("pdsi_suit field missing — re-run PDSI join")
    print(f"       OK")
except Exception as e:
    print(f"       FAIL or re-join needed: {e}")
    # Re-run PDSI join
    try:
        import numpy as np
        PDSI_TXT = f"{BASE}/07_hazards/raw/drought/pdsi/climdiv-pdsidv.txt"
        pdsi_records = []
        with open(PDSI_TXT) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                header = line[:10]
                vals_str = line[10:].split()
                ss = int(header[0:2]); dd = int(header[2:4]); yr = int(header[6:10])
                if yr < 2000: continue
                climdiv = ss * 100 + dd
                try:
                    vals = [float(v) for v in vals_str]
                    ann = np.mean([v for v in vals if v > -99])
                    pdsi_records.append({"climdiv": climdiv, "pdsi": ann})
                except: pass
        pdsi_mean = pd.DataFrame(pdsi_records).groupby("climdiv")["pdsi"].mean()
        pdsi_dict = pdsi_mean.to_dict()
        from osgeo import ogr
        pdsi_shp = f"{BASE}/07_hazards/raw/drought/pdsi/GIS.OFFICIAL_CLIM_DIVISIONS.shp"
        ds = ogr.Open(pdsi_shp, 1)
        lyr = ds.GetLayer(0)
        for field in ["pdsi_mean","pdsi_suit"]:
            if lyr.GetLayerDefn().GetFieldIndex(field) == -1:
                lyr.CreateField(ogr.FieldDefn(field, ogr.OFTReal))
        lyr.ResetReading(); lyr.StartTransaction()
        for feat in lyr:
            cd = feat.GetField("CLIMDIV")
            pval = pdsi_dict.get(cd, 0.0)
            suit = float(np.clip((pval + 4.0) / 8.0, 0.0, 1.0))
            feat.SetField("pdsi_mean", round(pval, 3))
            feat.SetField("pdsi_suit", round(suit, 4))
            lyr.SetFeature(feat)
        lyr.CommitTransaction(); ds = None
        print(f"       PDSI re-joined OK")
    except Exception as e2:
        print(f"       PDSI re-join also failed: {e2}")

# ── A3: FERC Queue — aggregate queued MW by county FIPS ─────────
print("  [A3] FERC queue — aggregate by county FIPS")
try:
    ferc = pd.read_excel(
        f"{BASE}/02_power_grid/raw/ferc_queue/lbnl_queued_up.xlsx",
        sheet_name="03. Complete Queue Data", skiprows=1
    )
    ferc_active = ferc[
        ferc["q_status"].isin(["active","suspended"]) &
        ferc["state"].isin(STATES_7)
    ].copy()
    ferc_active["fips_clean"] = (
        ferc_active["fips_codes"].astype(str)
        .str.split("/").str[0].str.strip()
        .str.replace(r"\.0$","",regex=True).str.zfill(5)
    )
    ferc_active["mw_total"] = pd.to_numeric(ferc_active["mw1"], errors="coerce").fillna(0)
    county_mw = ferc_active.groupby("fips_clean")["mw_total"].sum().reset_index()
    county_mw.columns = ["GEOID","queued_mw"]
    county_mw.to_csv(f"{TEMP}/ferc_county_mw.csv", index=False)
    print(f"       {len(county_mw)} counties | total {ferc_active['mw_total'].sum():,.0f} MW")
    print(f"       Saved: {TEMP}/ferc_county_mw.csv")
except Exception as e:
    print(f"       FAIL: {e}")

# ── A4: EIA retail prices — state level ─────────────────────────
print("  [A4] EIA retail electricity prices")
try:
    eia = pd.read_excel(
        f"{BASE}/02_power_grid/raw/ferc_queue/eia_retail_prices_by_state.xlsx",
        sheet_name="Price", header=1
    )
    eia.columns = [str(c).strip() for c in eia.columns]
    eia_7 = eia[eia["State"].isin(STATES_7)].copy()
    eia_7["Year"] = pd.to_numeric(eia_7["Year"], errors="coerce")
    eia_recent = eia_7.sort_values("Year",ascending=False).groupby("State").first().reset_index()
    price_col = "Industrial" if "Industrial" in eia_recent.columns else "Commercial"
    eia_recent["price"] = pd.to_numeric(eia_recent[price_col], errors="coerce")
    p_min = eia_recent["price"].min(); p_max = eia_recent["price"].max()
    eia_recent["price_suit"] = (p_max - eia_recent["price"]) / (p_max - p_min)
    # Map abbr to full name for state layer join
    abbr_to_name = {v:k for k,v in {
        "Arizona":"AZ","Illinois":"IL","Iowa":"IA",
        "Oregon":"OR","Texas":"TX","Virginia":"VA","West Virginia":"WV"
    }.items()}
    eia_recent["state_name"] = eia_recent["State"].map(abbr_to_name)
    out = eia_recent[["State","state_name","price","price_suit"]]
    out.to_csv(f"{TEMP}/eia_state_prices.csv", index=False)
    print(f"       Prices (¢/kWh): {dict(zip(eia_recent['State'],eia_recent['price'].round(2)))}")
    print(f"       Suitability:    {dict(zip(eia_recent['State'],eia_recent['price_suit'].round(3)))}")
    print(f"       Saved: {TEMP}/eia_state_prices.csv")
except Exception as e:
    print(f"       FAIL: {e}")

print("  [A] Data preparation complete")
PYEOF

# ────────────────────────────────────────────────────────────────
# STAGE B: Join FERC/EIA data to spatial layers using QGIS Python
# ────────────────────────────────────────────────────────────────
echo ""
echo "[B] Spatial joins (QGIS Python)"

$QGIS_PY - << 'PYEOF2'
import os, sys, csv
import numpy as np
sys.path.insert(0, "/Applications/QGIS-LTR.app/Contents/MacOS/lib/python3.9/site-packages")
os.environ["PROJ_LIB"] = "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj"
os.environ["GDAL_DATA"] = "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"

from osgeo import ogr, gdal
gdal.UseExceptions()

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
TEMP = "/tmp/step11"

# ── B1: Join FERC MW to county layer ───────────────────────────
print("  [B1] Join FERC MW to county GPKG")
try:
    ferc_csv = f"{TEMP}/ferc_county_mw.csv"
    ferc_dict = {}
    with open(ferc_csv) as f:
        for row in csv.DictReader(f):
            ferc_dict[row["GEOID"].zfill(5)] = float(row["queued_mw"])

    county_src = f"{BASE}/11_processed_layers/counties7_EPSG5070.gpkg"
    county_out = f"{TEMP}/counties_ferc.gpkg"
    drv = ogr.GetDriverByName("GPKG")
    src = ogr.Open(county_src)
    out_ds = drv.CopyDataSource(src, county_out)
    src = None
    lyr = out_ds.GetLayer(0)
    if lyr.GetLayerDefn().GetFieldIndex("queued_mw") == -1:
        lyr.CreateField(ogr.FieldDefn("queued_mw", ogr.OFTReal))
    lyr.ResetReading()
    lyr.StartTransaction()
    for feat in lyr:
        gid = str(feat.GetField("GEOID")).zfill(5)
        feat.SetField("queued_mw", ferc_dict.get(gid, 0.0))
        lyr.SetFeature(feat)
    lyr.CommitTransaction()
    layer_name = lyr.GetName()
    out_ds = None
    print(f"       OK — county FERC join saved, layer={layer_name}")
    print(f"       FERC_LAYER_NAME={layer_name}")  # for bash to capture
except Exception as e:
    print(f"       FAIL: {e}")

# ── B2: Join EIA prices to state layer ──────────────────────────
print("  [B2] Join EIA prices to state GPKG")
try:
    eia_csv = f"{TEMP}/eia_state_prices.csv"
    eia_dict = {}
    with open(eia_csv) as f:
        for row in csv.DictReader(f):
            eia_dict[row["state_name"]] = float(row["price_suit"])

    state_src = f"{BASE}/11_processed_layers/states7_reprojected_EPSG5070.gpkg"
    state_out = f"{TEMP}/states_eia.gpkg"
    drv = ogr.GetDriverByName("GPKG")
    src = ogr.Open(state_src)
    out_ds = drv.CopyDataSource(src, state_out)
    src = None
    lyr = out_ds.GetLayer(0)
    if lyr.GetLayerDefn().GetFieldIndex("price_suit") == -1:
        lyr.CreateField(ogr.FieldDefn("price_suit", ogr.OFTReal))
    lyr.ResetReading()
    lyr.StartTransaction()
    for feat in lyr:
        name = feat.GetField("Name") or ""
        feat.SetField("price_suit", eia_dict.get(name, -9999.0))
        lyr.SetFeature(feat)
    lyr.CommitTransaction()
    state_layer_name = lyr.GetName()
    out_ds = None
    print(f"       OK — state EIA join saved, layer={state_layer_name}")
    print(f"       STATE_LAYER_NAME={state_layer_name}")
except Exception as e:
    print(f"       FAIL: {e}")

print("  [B] Spatial joins complete")
PYEOF2

# ── Capture layer names ──────────────────────────────────────────
FERC_LAYER=$(ogrinfo /tmp/step11/counties_ferc.gpkg 2>/dev/null | grep "^1:" | awk '{print $2}')
STATE_LAYER=$(ogrinfo /tmp/step11/states_eia.gpkg 2>/dev/null | grep "^1:" | awk '{print $2}')
echo "  County FERC layer: $FERC_LAYER"
echo "  State EIA layer:   $STATE_LAYER"

# ────────────────────────────────────────────────────────────────
# STAGE C: GDAL rasterization
# ────────────────────────────────────────────────────────────────
echo ""
echo "[C] GDAL rasterization"

rasterize_and_warp() {
    local GPKG="$1" LAYER="$2" FIELD="$3" OUT="$4" SRS="${5:-EPSG:5070}"
    local TMP_WGS="${TEMP}/${FIELD}_wgs84.tif"
    echo "  Rasterizing $FIELD -> $(basename $OUT)"

    if [ "$SRS" = "EPSG:4326" ]; then
        # Vector in WGS84 — rasterize directly in WGS84, then warp
        "$GDAL_BIN/gdal_rasterize" \
            -a "$FIELD" -tr 0.1 0.1 \
            -te -130 22 -60 55 \
            -a_nodata $ND -ot Float32 \
            -l "$LAYER" "$GPKG" "$TMP_WGS" 2>/dev/null
        "$GDAL_BIN/gdalwarp" \
            -t_srs EPSG:5070 -tr 1000 1000 \
            -te $XMIN $YMIN $XMAX $YMAX \
            -r average -ot Float32 -dstnodata $ND \
            -co COMPRESS=LZW -co TILED=YES \
            -overwrite "$TMP_WGS" "$OUT" 2>/dev/null
    else
        # Vector already in EPSG:5070 — rasterize directly
        "$GDAL_BIN/gdal_rasterize" \
            -a "$FIELD" -tr 1000 1000 \
            -te $XMIN $YMIN $XMAX $YMAX \
            -a_srs EPSG:5070 \
            -a_nodata $ND -ot Float32 \
            -l "$LAYER" "$GPKG" "$OUT" 2>/dev/null
    fi
    echo "    -> $(ls -lh $OUT 2>/dev/null | awk '{print $5}') | $(basename $OUT)"
}

# C1: Aqueduct IAV
echo "  [C1] Aqueduct IAV suitability"
rasterize_and_warp "$TEMP/aqueduct_extra.gpkg" "baseline_annual" "iav_suit" \
    "$RASTERS/aqueduct_iav_suitability_1km.tif" "EPSG:4326"

# C2: Aqueduct GTD
echo "  [C2] Aqueduct GTD suitability"
rasterize_and_warp "$TEMP/aqueduct_extra.gpkg" "baseline_annual" "gtd_suit" \
    "$RASTERS/aqueduct_gtd_suitability_1km.tif" "EPSG:4326"

# C3: PDSI — export shapefile to GPKG first
echo "  [C3] PDSI drought suitability"
"$GDAL_BIN/ogr2ogr" -f GPKG -overwrite \
    "$TEMP/pdsi.gpkg" \
    "$BASE/07_hazards/raw/drought/pdsi/GIS.OFFICIAL_CLIM_DIVISIONS.shp" 2>/dev/null
PDSI_LAYER=$(ogrinfo "$TEMP/pdsi.gpkg" 2>/dev/null | grep "^1:" | awk '{print $2}')
echo "    PDSI layer: $PDSI_LAYER"
rasterize_and_warp "$TEMP/pdsi.gpkg" "$PDSI_LAYER" "pdsi_suit" \
    "$RASTERS/pdsi_mean_suitability_1km.tif" "EPSG:4326"

# C4: FERC queue density (raw MW)
echo "  [C4] FERC queue MW density"
rasterize_and_warp "$TEMP/counties_ferc.gpkg" "$FERC_LAYER" "queued_mw" \
    "$RASTERS/ferc_queue_mw_density_1km.tif" "EPSG:5070"

# C5: EIA retail price suitability
echo "  [C5] EIA retail price suitability"
rasterize_and_warp "$TEMP/states_eia.gpkg" "$STATE_LAYER" "price_suit" \
    "$RASTERS/eia_retail_price_suitability_1km.tif" "EPSG:5070"

# ────────────────────────────────────────────────────────────────
# STAGE D: Mask + invert FERC + SAIDI flag (QGIS Python)
# ────────────────────────────────────────────────────────────────
echo ""
echo "[D] Apply mask, invert FERC, create SAIDI flag"

$QGIS_PY - << 'PYEOF3'
import os, sys
import numpy as np
sys.path.insert(0, "/Applications/QGIS-LTR.app/Contents/MacOS/lib/python3.9/site-packages")
os.environ["PROJ_LIB"] = "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj"

from osgeo import gdal
gdal.UseExceptions()

BASE   = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RASTS  = f"{BASE}/11_processed_layers/rasters"
MASK_P = f"{RASTS}/mask_7states_1km_EPSG5070.tif"
ND     = -9999.0

def load(path):
    ds = gdal.Open(path)
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    return ds, arr

def save_masked(arr, template_ds, out_path):
    drv  = gdal.GetDriverByName("GTiff")
    opts = ["COMPRESS=LZW","TILED=YES"]
    out  = drv.Create(out_path, template_ds.RasterXSize, template_ds.RasterYSize,
                      1, gdal.GDT_Float32, opts)
    out.SetGeoTransform(template_ds.GetGeoTransform())
    out.SetProjection(template_ds.GetProjection())
    out.GetRasterBand(1).WriteArray(arr)
    out.GetRasterBand(1).SetNoDataValue(ND)
    out.FlushCache(); out = None

_, mask = load(MASK_P)
ref_ds, _  = load(MASK_P)

layers_to_mask = [
    "aqueduct_iav_suitability_1km.tif",
    "aqueduct_gtd_suitability_1km.tif",
    "pdsi_mean_suitability_1km.tif",
    "ferc_queue_mw_density_1km.tif",
    "eia_retail_price_suitability_1km.tif",
]

for fname in layers_to_mask:
    path = f"{RASTS}/{fname}"
    if not os.path.exists(path):
        print(f"  SKIP (not found): {fname}")
        continue
    _, arr = load(path)
    # Apply 7-state mask
    arr_masked = np.where(mask == 1, arr, ND)
    save_masked(arr_masked, ref_ds, path)
    valid = np.sum((arr_masked != ND) & (~np.isnan(arr_masked)))
    mean  = np.nanmean(arr_masked[arr_masked != ND]) if valid > 0 else float('nan')
    print(f"  Masked {fname}: {valid:,} cells, mean={mean:.3f}")

# Invert FERC density → suitability
ferc_raw = f"{RASTS}/ferc_queue_mw_density_1km.tif"
ferc_suit = f"{RASTS}/ferc_queue_suitability_1km.tif"
if os.path.exists(ferc_raw):
    _, arr_f = load(ferc_raw)
    valid_mw = arr_f[(arr_f != ND) & (arr_f > 0)]
    p99 = np.percentile(valid_mw, 99) if len(valid_mw) > 0 else 1.0
    suit_f = np.where(
        arr_f == ND, ND,
        np.where(arr_f <= 0, 1.0, np.clip(1.0 - arr_f / p99, 0.0, 1.0))
    ).astype(np.float32)
    suit_f[mask != 1] = ND
    save_masked(suit_f, ref_ds, ferc_suit)
    valid = np.sum(suit_f != ND)
    print(f"  FERC suit (p99={p99:,.0f} MW): {valid:,} cells, mean={np.mean(suit_f[suit_f!=ND]):.3f}")

# SAIDI NoData flag (1=has data, 0=gap)
saidi_s = f"{RASTS}/saidi_option_a_custweighted_suitability.tif"
saidi_flag = f"{RASTS}/saidi_nodata_flag_1km.tif"
if os.path.exists(saidi_s):
    _, arr_s = load(saidi_s)
    flag = np.where(mask == 1,
                    np.where(arr_s == ND, 0.0, 1.0),
                    ND).astype(np.float32)
    save_masked(flag, ref_ds, saidi_flag)
    has  = np.sum(flag == 1.0)
    miss = np.sum(flag == 0.0)
    tot  = has + miss
    print(f"  SAIDI flag: {has:,} cells with data ({has/tot*100:.1f}%), "
          f"{miss:,} NoData gap ({miss/tot*100:.1f}%)")

ref_ds = None
print("  [D] Complete")
PYEOF3

# ────────────────────────────────────────────────────────────────
# SUMMARY
# ────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "STEP 11 COMPLETE — Output files:"
echo "============================================================"
declare -A DESCS=(
    ["aqueduct_iav_suitability_1km.tif"]="Water interannual variability suitability"
    ["aqueduct_gtd_suitability_1km.tif"]="Groundwater table decline suitability"
    ["pdsi_mean_suitability_1km.tif"]="PDSI long-term drought suitability (2000-2024)"
    ["ferc_queue_mw_density_1km.tif"]="FERC active queued MW by county (raw)"
    ["ferc_queue_suitability_1km.tif"]="FERC congestion suitability (low queue = good)"
    ["eia_retail_price_suitability_1km.tif"]="EIA industrial price suitability (cheap = good)"
    ["saidi_nodata_flag_1km.tif"]="SAIDI data coverage flag (1=has data)"
)

for fname in "${!DESCS[@]}"; do
    path="$RASTERS/$fname"
    if [ -f "$path" ]; then
        size=$(ls -lh "$path" | awk '{print $5}')
        echo "  ✅ $fname ($size)"
        echo "     ${DESCS[$fname]}"
    else
        echo "  ❌ $fname — NOT CREATED"
    fi
done
