"""
Step 11 — Process supplementary grid availability and water scarcity layers
===========================================================================
Outputs (all EPSG:5070, 1 km, NoData=-9999, Float32):

Water scarcity:
  11_processed_layers/rasters/aqueduct_iav_suitability_1km.tif
      Interannual water variability suitability (1=most reliable, 0=most variable)
  11_processed_layers/rasters/aqueduct_gtd_suitability_1km.tif
      Groundwater table decline suitability (1=stable, 0=rapidly declining)
  11_processed_layers/rasters/pdsi_mean_suitability_1km.tif
      Long-term PDSI drought suitability (1=wet/no drought, 0=severe drought)

Grid availability proxies:
  11_processed_layers/rasters/ferc_queue_mw_density_1km.tif
      Total active queued MW per county → congestion proxy (0=low congestion=better)
  11_processed_layers/rasters/ferc_queue_suitability_1km.tif
      Inverted congestion suitability (1=low congestion=good, 0=highly congested)
  11_processed_layers/rasters/eia_retail_price_suitability_1km.tif
      Industrial electricity price suitability (1=cheapest state, 0=most expensive)

Grid reliability:
  11_processed_layers/rasters/saidi_nodata_flag_1km.tif
      Flag: 1=has SAIDI data, 0=NoData gap (28.5% of cells)
      (SAIDI suitability raster already exists at saidi_option_a_custweighted_suitability.tif)
"""

import os, sys, subprocess, zipfile
import numpy as np
import pandas as pd

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
os.chdir(BASE)

QGIS_PY  = "/Applications/QGIS-LTR.app/Contents/MacOS/bin/python3"
GIS_PY   = f"{BASE}/13_scripts/gis_venv/bin/python3"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
PROJ_LIB = "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj"
GDAL_DATA= "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"

# Reference grid parameters (from mask raster)
XMIN, YMIN, XMAX, YMAX = -2295000, 310000, 1791000, 2907000
RES = 1000
EPSG = "EPSG:5070"
NODATA = -9999

STATES_7 = {"AZ","IL","IA","OR","TX","VA","WV"}
RASTER_DIR = f"{BASE}/11_processed_layers/rasters"
TEMP_DIR = "/tmp/step11"
os.makedirs(TEMP_DIR, exist_ok=True)

env = {**os.environ, "PROJ_LIB": PROJ_LIB, "GDAL_DATA": GDAL_DATA}

def gdal_run(cmd):
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  WARN: {' '.join(cmd[:3])} returned {result.returncode}")
        if result.stderr: print(f"  {result.stderr[:200]}")
    return result.returncode == 0

def warp_to_grid(src, dst, resampling="average", dtype="Float32"):
    """Warp any raster to the reference 1km EPSG:5070 grid."""
    return gdal_run([
        f"{GDAL_BIN}/gdalwarp",
        "-t_srs", EPSG, "-tr", str(RES), str(RES),
        "-te", str(XMIN), str(YMIN), str(XMAX), str(YMAX),
        "-r", resampling, "-ot", dtype,
        "-dstnodata", str(NODATA),
        "-co", "COMPRESS=LZW", "-co", "TILED=YES",
        "-overwrite", src, dst
    ])

def apply_mask(raster):
    """Zero out cells outside 7-state mask (set to NODATA)."""
    mask_path = f"{RASTER_DIR}/mask_7states_1km_EPSG5070.tif"
    tmp = raster.replace(".tif", "_premask.tif")
    os.rename(raster, tmp)
    gdal_run([
        f"{GDAL_BIN}/gdal_calc.py",
        "-A", tmp, "-B", mask_path,
        f"--outfile={raster}",
        "--calc=numpy.where((B==1)&(A!={NODATA}), A, {NODATA})",
        "--type=Float32", f"--NoDataValue={NODATA}",
        "--co=COMPRESS=LZW", "--co=TILED=YES", "--overwrite"
    ])
    os.remove(tmp)

print("=" * 60)
print("STEP 11 — Supplementary layer processing")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# LAYER 1 & 2 — Aqueduct IAV and GTD
# ══════════════════════════════════════════════════════════════
print("\n[1/7] Aqueduct interannual variability (IAV) + groundwater decline (GTD)")

GDB = f"{BASE}/05_water_stress/raw/aqueduct_gdb/GDB/Aq40_Y2023D07M05.gdb"

# Export from GDB to GeoPackage with iav_score and gtd_score
aq_gpkg = f"{TEMP_DIR}/aqueduct_extra.gpkg"
result = subprocess.run([
    f"{GDAL_BIN}/ogr2ogr", "-f", "GPKG", aq_gpkg, GDB,
    "baseline_annual",
    "-select", "aq30_id,gid_0,iav_score,gtd_score,drr_score",
    "-overwrite"
], env=env, capture_output=True, text=True)
print(f"  GDB export: {'OK' if result.returncode==0 else 'FAIL'}")

# Replace -9999 values in GTD with 0 (insignificant decline = no penalty)
# using Python/GDAL
from osgeo import ogr, gdal
gdal.UseExceptions()

ds = ogr.Open(aq_gpkg, 1)
lyr = ds.GetLayer(0)
print(f"  Aqueduct features: {lyr.GetFeatureCount()}")

# Add computed suitability fields
for field in ["iav_suit", "gtd_suit"]:
    if lyr.GetLayerDefn().GetFieldIndex(field) == -1:
        lyr.CreateField(ogr.FieldDefn(field, ogr.OFTReal))

lyr.ResetReading()
lyr.StartTransaction()
for feat in lyr:
    iav = feat.GetField("iav_score")
    gtd = feat.GetField("gtd_score")
    # IAV: score 0-5; higher=worse; suit = 1 - score/5
    iav_s = max(0.0, 1.0 - iav/5.0) if iav is not None and iav >= 0 else 1.0
    # GTD: score -9999 (insignificant) or 0-5; suit = 1 - max(0,score)/5
    if gtd is None or gtd < 0:
        gtd_s = 1.0   # no data = assume stable = good
    else:
        gtd_s = max(0.0, 1.0 - gtd/5.0)
    feat.SetField("iav_suit", round(iav_s, 4))
    feat.SetField("gtd_suit", round(gtd_s, 4))
    lyr.SetFeature(feat)
lyr.CommitTransaction()
ds = None

# Rasterize iav_suit
for field, outname in [("iav_suit","aqueduct_iav_suitability_1km"),
                        ("gtd_suit","aqueduct_gtd_suitability_1km")]:
    out = f"{RASTER_DIR}/{outname}.tif"
    # First rasterize in WGS84, then warp
    tmp_wgs = f"{TEMP_DIR}/{outname}_wgs84.tif"
    gdal_run([
        f"{GDAL_BIN}/gdal_rasterize",
        "-a", field,
        "-tr", "0.1", "0.1",
        "-te", "-130", "22", "-60", "55",
        "-a_nodata", str(NODATA),
        "-ot", "Float32",
        "-l", "aqueduct_extra",
        aq_gpkg, tmp_wgs
    ])
    warp_to_grid(tmp_wgs, out, resampling="average")
    apply_mask(out)
    # Stats
    ds_r = gdal.Open(out)
    band = ds_r.GetRasterBand(1)
    arr = band.ReadAsArray().astype(float)
    arr[arr == NODATA] = np.nan
    valid = np.sum(~np.isnan(arr))
    print(f"  {outname}: {valid:,} valid cells, mean={np.nanmean(arr):.3f}, "
          f"range [{np.nanmin(arr):.3f},{np.nanmax(arr):.3f}]")
    ds_r = None

# ══════════════════════════════════════════════════════════════
# LAYER 3 — PDSI long-term mean drought suitability
# ══════════════════════════════════════════════════════════════
print("\n[2/7] PDSI long-term drought suitability (2000–2024)")

PDSI_SHP = f"{BASE}/07_hazards/raw/drought/pdsi/GIS.OFFICIAL_CLIM_DIVISIONS.shp"
PDSI_TXT = f"{BASE}/07_hazards/raw/drought/pdsi/climdiv-pdsidv.txt"

# Parse PDSI text file
# Format: SSDDEE YYYY  v01  v02 ... v12
# SS=NOAA state code (2), DD=division (2), EE=element (2, 05=PDSI), YYYY=year
pdsi_records = []
with open(PDSI_TXT) as f:
    for line in f:
        line = line.strip()
        if not line: continue
        header = line[:10]
        vals_str = line[10:].split()
        ss = int(header[0:2])
        dd = int(header[2:4])
        # ee = int(header[4:6])  # should be 05
        yr = int(header[6:10])
        if yr < 2000: continue  # only use 2000–present
        climdiv = ss * 100 + dd
        try:
            vals = [float(v) for v in vals_str]
            ann_mean = np.mean([v for v in vals if v > -99])
            pdsi_records.append({"climdiv": climdiv, "year": yr, "pdsi": ann_mean})
        except:
            pass

pdf = pd.DataFrame(pdsi_records)
# Long-term mean per division
pdsi_mean = pdf.groupby("climdiv")["pdsi"].mean().reset_index()
pdsi_mean.columns = ["climdiv", "pdsi_mean"]
print(f"  Parsed {len(pdsi_mean)} PDSI climate divisions (2000-2024 mean)")
print(f"  PDSI range: {pdsi_mean['pdsi_mean'].min():.2f} to {pdsi_mean['pdsi_mean'].max():.2f}")

# Load shapefile and join PDSI
ds_shp = ogr.Open(PDSI_SHP, 1)
lyr_shp = ds_shp.GetLayer(0)
if lyr_shp.GetLayerDefn().GetFieldIndex("pdsi_mean") == -1:
    lyr_shp.CreateField(ogr.FieldDefn("pdsi_mean", ogr.OFTReal))
if lyr_shp.GetLayerDefn().GetFieldIndex("pdsi_suit") == -1:
    lyr_shp.CreateField(ogr.FieldDefn("pdsi_suit", ogr.OFTReal))

pdsi_dict = dict(zip(pdsi_mean["climdiv"], pdsi_mean["pdsi_mean"]))

lyr_shp.ResetReading()
lyr_shp.StartTransaction()
matched = 0
for feat in lyr_shp:
    climdiv = feat.GetField("CLIMDIV")
    if climdiv in pdsi_dict:
        pval = pdsi_dict[climdiv]
        # Suitability: PDSI -4 to +4 range; map to 0-1
        # Very dry (<-4) = 0.0; Normal (0) = 0.5; Wet (>4) = 1.0
        # But for DC: moderate (not too wet, not too dry) might be ideal
        # However convention: less drought = better = higher suitability
        suit = float(np.clip((pval + 4.0) / 8.0, 0.0, 1.0))
        feat.SetField("pdsi_mean", round(pval, 3))
        feat.SetField("pdsi_suit", round(suit, 4))
        lyr_shp.SetFeature(feat)
        matched += 1
lyr_shp.CommitTransaction()
ds_shp = None
print(f"  Joined PDSI to {matched} shapefile divisions")

# Export to temp GPKG and rasterize
pdsi_gpkg = f"{TEMP_DIR}/pdsi_divisions.gpkg"
gdal_run([f"{GDAL_BIN}/ogr2ogr", "-f", "GPKG", pdsi_gpkg, PDSI_SHP,
          "-t_srs", "EPSG:4326", "-overwrite"])

pdsi_tmp = f"{TEMP_DIR}/pdsi_wgs84.tif"
gdal_run([
    f"{GDAL_BIN}/gdal_rasterize",
    "-a", "pdsi_suit",
    "-tr", "0.1", "0.1",
    "-te", "-130", "22", "-60", "55",
    "-a_nodata", str(NODATA), "-ot", "Float32",
    "-l", "GIS.OFFICIAL_CLIM_DIVISIONS",
    pdsi_gpkg, pdsi_tmp
])

pdsi_out = f"{RASTER_DIR}/pdsi_mean_suitability_1km.tif"
warp_to_grid(pdsi_tmp, pdsi_out, resampling="average")
apply_mask(pdsi_out)

ds_r = gdal.Open(pdsi_out)
arr = ds_r.GetRasterBand(1).ReadAsArray().astype(float)
arr[arr == NODATA] = np.nan
print(f"  pdsi_mean_suitability: {np.sum(~np.isnan(arr)):,} valid cells, "
      f"mean={np.nanmean(arr):.3f}, range [{np.nanmin(arr):.3f},{np.nanmax(arr):.3f}]")
ds_r = None

# ══════════════════════════════════════════════════════════════
# LAYER 4 & 5 — FERC Queue density (congestion proxy)
# ══════════════════════════════════════════════════════════════
print("\n[3/7] FERC interconnection queue — congestion proxy")

ferc = pd.read_excel(
    f"{BASE}/02_power_grid/raw/ferc_queue/lbnl_queued_up.xlsx",
    sheet_name="03. Complete Queue Data", skiprows=1
)
print(f"  FERC total records: {len(ferc)}")

# Filter: active/suspended projects in 7 states
ferc_active = ferc[
    ferc["q_status"].isin(["active","suspended"]) &
    ferc["state"].isin(STATES_7)
].copy()
print(f"  Active/suspended in 7 states: {len(ferc_active)}")

# Parse county FIPS (may contain multiple separated by /)
ferc_active["fips_clean"] = (ferc_active["fips_codes"]
    .astype(str).str.split("/").str[0]
    .str.strip().str.replace(r"\.0$","",regex=True))

# Aggregate queued MW by county FIPS
ferc_active["mw_total"] = ferc_active["mw1"].fillna(0)
county_mw = (ferc_active.groupby("fips_clean")["mw_total"]
             .sum().reset_index())
county_mw.columns = ["GEOID","queued_mw"]
county_mw["GEOID"] = county_mw["GEOID"].str.zfill(5)
print(f"  Counties with active queue: {len(county_mw)}")
print(f"  Total queued MW in 7 states: {ferc_active['mw_total'].sum():,.0f} MW")

# Find county vector layer
county_gpkg = None
for f in os.listdir(f"{BASE}/11_processed_layers"):
    if "count" in f.lower() and f.endswith(".gpkg"):
        county_gpkg = f"{BASE}/11_processed_layers/{f}"
        break
if county_gpkg is None:
    # Try raw data
    for root,dirs,files in os.walk(f"{BASE}"):
        for f in files:
            if "county" in f.lower() and f.endswith((".gpkg",".shp")):
                county_gpkg = os.path.join(root,f)
                break
        if county_gpkg: break

print(f"  County layer: {county_gpkg}")

if county_gpkg:
    # Join queued_mw to county layer
    county_join = f"{TEMP_DIR}/counties_ferc.gpkg"
    subprocess.run([f"{GDAL_BIN}/ogr2ogr", "-f", "GPKG",
                    county_join, county_gpkg, "-overwrite"], env=env)

    ds_c = ogr.Open(county_join, 1)
    lyr_c = ds_c.GetLayer(0)
    # Find GEOID field
    defn = lyr_c.GetLayerDefn()
    geoid_field = None
    for i in range(defn.GetFieldCount()):
        fn = defn.GetFieldDefn(i).GetName()
        if fn.upper() in ("GEOID","GEOID10","GEOID20","FIPS","COUNTYFIPS"):
            geoid_field = fn; break
    print(f"  County GEOID field: {geoid_field}")

    if geoid_field:
        mw_dict = dict(zip(county_mw["GEOID"], county_mw["queued_mw"]))
        if lyr_c.GetLayerDefn().GetFieldIndex("queued_mw") == -1:
            lyr_c.CreateField(ogr.FieldDefn("queued_mw", ogr.OFTReal))
        lyr_c.ResetReading()
        lyr_c.StartTransaction()
        for feat in lyr_c:
            gid = str(feat.GetField(geoid_field)).zfill(5)
            feat.SetField("queued_mw", mw_dict.get(gid, 0.0))
            lyr_c.SetFeature(feat)
        lyr_c.CommitTransaction()
    ds_c = None

    # Rasterize queued_mw
    ferc_raw_tif = f"{RASTER_DIR}/ferc_queue_mw_density_1km.tif"
    gdal_run([
        f"{GDAL_BIN}/gdal_rasterize",
        "-a", "queued_mw",
        "-tr", str(RES), str(RES),
        "-te", str(XMIN), str(YMIN), str(XMAX), str(YMAX),
        "-a_srs", EPSG,
        "-a_nodata", "0",   # 0 = no queue data (not NoData)
        "-ot", "Float32",
        "-l", lyr_c.GetName() if hasattr(lyr_c,"GetName") else "counties_ferc",
        county_join, ferc_raw_tif
    ])

    # Invert to suitability: low congestion = high suitability
    # Normalise: suit = 1 - clip(mw / 99th_pct, 0, 1)
    ds_f = gdal.Open(ferc_raw_tif)
    arr_f = ds_f.GetRasterBand(1).ReadAsArray().astype(float)
    ds_f = None

    p99 = np.percentile(arr_f[arr_f > 0], 99) if np.any(arr_f > 0) else 1
    print(f"  Queued MW 99th pct (non-zero counties): {p99:,.0f} MW")

    suit_f = np.where(arr_f <= 0,
                      1.0,                              # no queue = best
                      np.clip(1.0 - arr_f / p99, 0, 1))
    suit_f = suit_f.astype(np.float32)

    # Write suitability raster
    ferc_suit_tif = f"{RASTER_DIR}/ferc_queue_suitability_1km.tif"
    drv = gdal.GetDriverByName("GTiff")
    ref_ds = gdal.Open(f"{RASTER_DIR}/mask_7states_1km_EPSG5070.tif")
    out_ds = drv.Create(ferc_suit_tif, ref_ds.RasterXSize, ref_ds.RasterYSize,
                        1, gdal.GDT_Float32,
                        ["COMPRESS=LZW","TILED=YES"])
    out_ds.SetGeoTransform(ref_ds.GetGeoTransform())
    out_ds.SetProjection(ref_ds.GetProjection())
    mask_arr = ref_ds.GetRasterBand(1).ReadAsArray()
    suit_f[mask_arr != 1] = NODATA
    out_ds.GetRasterBand(1).WriteArray(suit_f)
    out_ds.GetRasterBand(1).SetNoDataValue(NODATA)
    out_ds.FlushCache()
    out_ds = ref_ds = None
    valid_ferc = np.sum(suit_f != NODATA)
    print(f"  ferc_queue_suitability: {valid_ferc:,} cells, "
          f"mean={np.mean(suit_f[suit_f!=NODATA]):.3f}")
else:
    print("  WARN: County layer not found — skipping FERC rasterization")

# ══════════════════════════════════════════════════════════════
# LAYER 6 — EIA Retail Electricity Price suitability
# ══════════════════════════════════════════════════════════════
print("\n[4/7] EIA retail electricity price suitability (by state)")

eia = pd.read_excel(
    f"{BASE}/02_power_grid/raw/ferc_queue/eia_retail_prices_by_state.xlsx",
    sheet_name="Price", header=1
)
eia.columns = [str(c).strip() for c in eia.columns]
# Column names: Year, State, Industry Sector Category, Residential, Commercial, Industrial...
print(f"  EIA columns: {list(eia.columns)}")

# Get most recent year for 7 states, Industrial sector
eia_7 = eia[eia["State"].isin(STATES_7)].copy()
eia_7["Year"] = pd.to_numeric(eia_7["Year"], errors="coerce")
eia_recent = eia_7.sort_values("Year", ascending=False).groupby("State").first().reset_index()
print(f"  Most recent year per state:\n{eia_recent[['State','Year']].to_string()}")

# Use Industrial price (data centres typically pay industrial/commercial rates)
price_col = "Industrial"
if price_col not in eia_recent.columns:
    price_col = "Commercial"
eia_recent["price"] = pd.to_numeric(eia_recent[price_col], errors="coerce")
print(f"\n  Industrial electricity price (¢/kWh) by state:")
for _,row in eia_recent.iterrows():
    print(f"    {row['State']}: {row['price']:.2f}¢/kWh")

# Normalize: lower price = better suitability
p_min = eia_recent["price"].min()
p_max = eia_recent["price"].max()
eia_recent["price_suit"] = (p_max - eia_recent["price"]) / (p_max - p_min)
price_suit_dict = dict(zip(eia_recent["State"], eia_recent["price_suit"]))
print(f"\n  Suitability scores: {price_suit_dict}")

# Rasterize: join to state boundaries in 7-state mask area
# Use the states vector layer
state_layer = None
for f in os.listdir(f"{BASE}/11_processed_layers"):
    if "state" in f.lower() and f.endswith(".gpkg"):
        state_layer = f"{BASE}/11_processed_layers/{f}"
        break

print(f"  State layer: {state_layer}")

if state_layer:
    state_join = f"{TEMP_DIR}/states_eia.gpkg"
    subprocess.run([f"{GDAL_BIN}/ogr2ogr", "-f", "GPKG",
                    state_join, state_layer, "-overwrite"], env=env)
    ds_s = ogr.Open(state_join, 1)
    lyr_s = ds_s.GetLayer(0)
    defn_s = lyr_s.GetLayerDefn()
    # Find state abbreviation field
    abbr_field = None
    for i in range(defn_s.GetFieldCount()):
        fn = defn_s.GetFieldDefn(i).GetName()
        if fn.upper() in ("STUSPS","STATE_ABBR","STATEABBR","ABBREV","ST"):
            abbr_field = fn; break
    print(f"  State abbr field: {abbr_field}")

    if abbr_field:
        if defn_s.GetFieldIndex("price_suit") == -1:
            lyr_s.CreateField(ogr.FieldDefn("price_suit", ogr.OFTReal))
        lyr_s.ResetReading()
        lyr_s.StartTransaction()
        for feat in lyr_s:
            st = feat.GetField(abbr_field)
            suit = price_suit_dict.get(st, NODATA)
            feat.SetField("price_suit", suit)
            lyr_s.SetFeature(feat)
        lyr_s.CommitTransaction()
    ds_s = None

    eia_tif = f"{RASTER_DIR}/eia_retail_price_suitability_1km.tif"
    gdal_run([
        f"{GDAL_BIN}/gdal_rasterize",
        "-a", "price_suit",
        "-tr", str(RES), str(RES),
        "-te", str(XMIN), str(YMIN), str(XMAX), str(YMAX),
        "-a_srs", EPSG, "-a_nodata", str(NODATA), "-ot", "Float32",
        "-l", lyr_s.GetName() if hasattr(lyr_s,"GetName") else "states_eia",
        state_join, eia_tif
    ])
    apply_mask(eia_tif)
    ds_r = gdal.Open(eia_tif)
    arr_e = ds_r.GetRasterBand(1).ReadAsArray().astype(float)
    arr_e[arr_e == NODATA] = np.nan
    print(f"  eia_retail_price_suitability: {np.sum(~np.isnan(arr_e)):,} valid cells")
    ds_r = None
else:
    print("  WARN: State layer not found — skipping EIA rasterization")

# ══════════════════════════════════════════════════════════════
# LAYER 7 — SAIDI NoData flag
# ══════════════════════════════════════════════════════════════
print("\n[5/7] SAIDI NoData flag (1=has data, 0=NoData gap)")

saidi_suit = f"{RASTER_DIR}/saidi_option_a_custweighted_suitability.tif"
saidi_flag = f"{RASTER_DIR}/saidi_nodata_flag_1km.tif"

gdal_run([
    f"{GDAL_BIN}/gdal_calc.py",
    "-A", saidi_suit,
    f"--outfile={saidi_flag}",
    f"--calc=numpy.where(A=={NODATA}, 0.0, 1.0)",
    "--type=Float32", f"--NoDataValue={NODATA}",
    "--co=COMPRESS=LZW", "--co=TILED=YES", "--overwrite"
])

ds_r = gdal.Open(saidi_flag)
arr_s = ds_r.GetRasterBand(1).ReadAsArray().astype(float)
has_data = np.sum(arr_s == 1.0)
no_data  = np.sum(arr_s == 0.0)
total    = has_data + no_data
print(f"  SAIDI coverage: {has_data:,} cells have data ({has_data/total*100:.1f}%)")
print(f"  SAIDI gap:      {no_data:,} cells missing ({no_data/total*100:.1f}%)")
ds_r = None

# ══════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 11 COMPLETE — New layers created:")
print("=" * 60)
outputs = [
    ("aqueduct_iav_suitability_1km.tif",      "Water interannual variability suit."),
    ("aqueduct_gtd_suitability_1km.tif",      "Groundwater table decline suit."),
    ("pdsi_mean_suitability_1km.tif",         "PDSI long-term drought suit."),
    ("ferc_queue_mw_density_1km.tif",         "FERC queue MW raw density"),
    ("ferc_queue_suitability_1km.tif",        "FERC queue congestion suit."),
    ("eia_retail_price_suitability_1km.tif",  "EIA retail electricity price suit."),
    ("saidi_nodata_flag_1km.tif",             "SAIDI coverage flag (1=has data)"),
]
for fname, desc in outputs:
    path = f"{RASTER_DIR}/{fname}"
    if os.path.exists(path):
        size_kb = os.path.getsize(path) // 1024
        print(f"  ✅ {fname}")
        print(f"     {desc} — {size_kb:,} KB")
    else:
        print(f"  ❌ {fname} — NOT CREATED")
