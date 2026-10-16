"""
V8 Sensitivity: Equal weights within ESI (water=wildfire=flood=1/3 each).
All other parameters identical to S1 baseline (ESI 50%, OFI 50%).
Computes Jaccard overlap of V8 top-decile vs. S1 top-decile.

Run with:
    ./gis_venv/bin/python3 step16_v8_equal_esi_weights.py
"""

import os, json, subprocess
import numpy as np

BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RDIR     = f"{BASE}/11_processed_layers/rasters"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
PROJ_ENV = {**os.environ,
            "PROJ_LIB":  "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj",
            "GDAL_DATA": "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"}

NROWS, NCOLS = 2597, 4086
XMIN, YMIN   = -2295000, 310000
RES          = 1000


def run(cmd):
    r = subprocess.run(cmd, env=PROJ_ENV, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr}")


def read_raster(tif):
    tmp = tif + ".tmp16.raw"
    run([f"{GDAL_BIN}/gdal_translate", "-of", "ENVI", "-ot", "Float32",
         "-co", "INTERLEAVE=BSQ", tif, tmp])
    arr = np.fromfile(tmp, dtype=np.float32).reshape(NROWS, NCOLS)
    for f in [tmp, tmp + ".hdr"]:
        try: os.remove(f)
        except: pass
    arr = arr.astype(np.float64)
    arr[(arr == -9999.0) | (arr == -9998.0)] = np.nan
    return arr


def write_raster(arr, path):
    tmp_raw = path + ".tmp16.raw"
    tmp_vrt = path + ".tmp16.vrt"
    a32 = arr.astype(np.float32)
    a32[np.isnan(arr)] = -9999.0
    a32.tofile(tmp_raw)

    hdr = (f"ENVI\nsamples = {NCOLS}\nlines = {NROWS}\nbands = 1\n"
           f"header offset = 0\nfile type = ENVI Standard\ndata type = 4\n"
           f"interleave = bsq\nbyte order = 0\n")
    with open(tmp_raw + ".hdr", "w") as f:
        f.write(hdr)

    ymax_c = YMIN + NROWS * RES
    vrt_xml = f"""<VRTDataset rasterXSize="{NCOLS}" rasterYSize="{NROWS}">
  <SRS>EPSG:5070</SRS>
  <GeoTransform>{XMIN}, {RES}, 0, {ymax_c}, 0, -{RES}</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1">
    <NoDataValue>-9999</NoDataValue>
    <SimpleSource>
      <SourceFilename relativeToVRT="0">{tmp_raw}</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="{NCOLS}" RasterYSize="{NROWS}"
                        DataType="Float32" BlockXSize="{NCOLS}" BlockYSize="1"/>
      <SrcRect xOff="0" yOff="0" xSize="{NCOLS}" ySize="{NROWS}"/>
      <DstRect xOff="0" yOff="0" xSize="{NCOLS}" ySize="{NROWS}"/>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>"""
    with open(tmp_vrt, "w") as f:
        f.write(vrt_xml)
    if os.path.exists(path): os.remove(path)
    run([f"{GDAL_BIN}/gdal_translate", "-of", "GTiff", "-ot", "Float32",
         "-a_nodata", "-9999", "-co", "COMPRESS=LZW", "-co", "TILED=YES",
         tmp_vrt, path])
    for f in [tmp_raw, tmp_raw + ".hdr", tmp_vrt]:
        try: os.remove(f)
        except: pass
    print(f"  → {os.path.basename(path)}")


print("\n=== V8: Equal weights within ESI (water=wildfire=flood=1/3) ===")

print("\n--- Loading rasters ---")
gric_s1  = read_raster(f"{RDIR}/gric_s1_baseline_1km.tif")
water_s  = read_raster(f"{RDIR}/water_stress_baseline_bws_suitability.tif")
wildfire = read_raster(f"{RDIR}/nri_wildfire_suitability_1km.tif")
flood    = read_raster(f"{RDIR}/nri_inland_flood_suitability_1km.tif")
tx230    = read_raster(f"{RDIR}/hifld_tx_230kV_proximity_1km.tif")
road     = read_raster(f"{RDIR}/tiger_roads_prisec_proximity_1km.tif")
print("  All loaded.")

# Eligible mask — wherever S1 was computed
eligible_mask = ~np.isnan(gric_s1)
print(f"  Eligible cells: {eligible_mask.sum():,}")

# OFI (identical to S1)
suit_tx   = np.clip(1.0 - tx230 / 100000.0, 0.0, 1.0); suit_tx[np.isnan(tx230)]  = np.nan
suit_road = np.clip(1.0 - road  /  30000.0, 0.0, 1.0); suit_road[np.isnan(road)] = np.nan
all_ofi_v = (~np.isnan(suit_tx)) & (~np.isnan(suit_road))
ofi = 0.70 * np.nan_to_num(suit_tx, nan=0) + 0.30 * np.nan_to_num(suit_road, nan=0)
ofi[~all_ofi_v] = np.nan

# V8 ESI — equal thirds
print("\n--- Computing V8 ESI (1/3, 1/3, 1/3) ---")
all_esi_v = (~np.isnan(water_s)) & (~np.isnan(wildfire)) & (~np.isnan(flood))
esi_v8 = (
    (1/3) * np.nan_to_num(water_s,  nan=0) +
    (1/3) * np.nan_to_num(wildfire, nan=0) +
    (1/3) * np.nan_to_num(flood,    nan=0)
)
esi_v8[~all_esi_v] = np.nan

# S1 ESI for comparison
esi_s1 = (
    (3/7) * np.nan_to_num(water_s,  nan=0) +
    (2/7) * np.nan_to_num(wildfire, nan=0) +
    (2/7) * np.nan_to_num(flood,    nan=0)
)
esi_s1[~all_esi_v] = np.nan

print(f"  ESI V8  mean: {np.nanmean(esi_v8[eligible_mask]):.4f}  std: {np.nanstd(esi_v8[eligible_mask]):.4f}")
print(f"  ESI S1  mean: {np.nanmean(esi_s1[eligible_mask]):.4f}  std: {np.nanstd(esi_s1[eligible_mask]):.4f}")
print(f"  Max ESI abs diff: {np.nanmax(np.abs(esi_v8 - esi_s1)):.4f}")

# GRIC V8 (ESI 50%, OFI 50%)
print("\n--- Computing GRIC V8 ---")
all_v   = (~np.isnan(esi_v8)) & (~np.isnan(ofi))
gric_v8 = 0.50 * np.nan_to_num(esi_v8, nan=0) + 0.50 * np.nan_to_num(ofi, nan=0)
gric_v8[~all_v] = np.nan

flat_v8 = gric_v8[eligible_mask & ~np.isnan(gric_v8)]
flat_s1 = gric_s1[eligible_mask & ~np.isnan(gric_s1)]
print(f"  V8  cells: {len(flat_v8):,}  mean: {np.mean(flat_v8):.4f}  p90: {np.percentile(flat_v8, 90):.4f}")
print(f"  S1  cells: {len(flat_s1):,}  mean: {np.mean(flat_s1):.4f}  p90: {np.percentile(flat_s1, 90):.4f}")

# Save raster
write_raster(gric_v8, f"{RDIR}/gric_v8_equal_esi_weights_1km.tif")

# Jaccard: top-decile overlap V8 vs S1
print("\n--- Jaccard top-decile overlap (V8 vs S1) ---")
q90_s1 = np.percentile(flat_s1, 90)
q90_v8 = np.percentile(flat_v8, 90)
top_s1 = (gric_s1 >= q90_s1) & eligible_mask & ~np.isnan(gric_s1)
top_v8 = (gric_v8 >= q90_v8) & eligible_mask & ~np.isnan(gric_v8)
inter  = int(np.sum(top_s1 & top_v8))
union  = int(np.sum(top_s1 | top_v8))
jaccard = inter / union if union > 0 else 0.0

print(f"  S1 top-decile cells : {top_s1.sum():,}  (threshold = {q90_s1:.4f})")
print(f"  V8 top-decile cells : {top_v8.sum():,}  (threshold = {q90_v8:.4f})")
print(f"  Intersection        : {inter:,}")
print(f"  Union               : {union:,}")
print(f"  Jaccard (V8 vs S1)  : {jaccard:.3f}")

# State-level breakdown
print("\n--- State top-decile shares: V8 vs S1 ---")
STATE_BBOX = {
    "AZ": (-1600000, -800000,  770000, 1400000),
    "IL": (  500000,  900000, 1580000, 1900000),
    "IA": (  200000,  800000, 1800000, 2100000),
    "OR": (-2200000,-1000000, 2200000, 2800000),
    "TX": ( -700000,  500000,  600000, 1400000),
    "VA": ( 1200000, 1791000, 1200000, 1600000),
    "WV": ( 1050000, 1450000, 1300000, 1650000),
}

def bbox_to_mask(xmin_s, xmax_s, ymin_s, ymax_s):
    c1 = max(0, int((xmin_s - XMIN) / RES))
    c2 = min(NCOLS, int((xmax_s - XMIN) / RES) + 1)
    r1 = max(0, int(((YMIN + NROWS * RES) - ymax_s) / RES))
    r2 = min(NROWS, int(((YMIN + NROWS * RES) - ymin_s) / RES) + 1)
    m  = np.zeros((NROWS, NCOLS), dtype=bool)
    if r1 < r2 and c1 < c2:
        m[r1:r2, c1:c2] = True
    return m & eligible_mask

print(f"  {'State':<6}  {'S1 share':>10}  {'V8 share':>10}  {'Δ':>8}")
print("  " + "-"*42)
state_results = {}
for state, bbox in STATE_BBOX.items():
    sm    = bbox_to_mask(*bbox)
    n_elig = sm.sum()
    if n_elig == 0:
        continue
    s_s1 = np.sum(top_s1 & sm) / n_elig * 100
    s_v8 = np.sum(top_v8 & sm) / n_elig * 100
    delta = s_v8 - s_s1
    print(f"  {state:<6}  {s_s1:>9.1f}%  {s_v8:>9.1f}%  {delta:>+7.1f}%")
    state_results[state] = {"s1_share": round(s_s1, 1), "v8_share": round(s_v8, 1), "delta": round(delta, 1)}

# Append to scenario_robustness.json
json_path = f"{BASE}/00_ADMIN/scenario_robustness.json"
if os.path.exists(json_path):
    with open(json_path) as f:
        rob = json.load(f)
else:
    rob = {"scenarios": {}, "state_top_decile_shares": {}}

rob["scenarios"]["V8_equal_ESI"] = {
    "label": "V8 Equal weights within ESI (1/3, 1/3, 1/3)",
    "jaccard_vs_s1": round(jaccard, 3),
    "n_top_decile": int(top_v8.sum()),
    "p90_threshold": round(float(q90_v8), 4),
    "weights": {"water": round(1/3, 4), "wildfire": round(1/3, 4), "flood": round(1/3, 4)},
}
for state, vals in state_results.items():
    if state not in rob["state_top_decile_shares"]:
        rob["state_top_decile_shares"][state] = {}
    rob["state_top_decile_shares"][state]["V8"] = vals["v8_share"]

with open(json_path, "w") as f:
    json.dump(rob, f, indent=2)
print(f"\n  → scenario_robustness.json updated")

print("\n=== V8 COMPLETE ===")
print(f"\n  RESULT: Jaccard (V8 vs S1) = {jaccard:.3f}")
w_diff = 1/3 - 3/7
print(f"  Water weight:    3/7={3/7:.4f} → 1/3={1/3:.4f}  ({w_diff:+.4f})")
print(f"  Wildfire weight: 2/7={2/7:.4f} → 1/3={1/3:.4f}  ({1/3-2/7:+.4f})")
print(f"  Flood weight:    2/7={2/7:.4f} → 1/3={1/3:.4f}  ({1/3-2/7:+.4f})")
