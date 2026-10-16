"""
step17_spearman_ofi5050.py

Two additions to strengthen sensitivity analysis:

1. Spearman rank correlation (ρ) for all existing sensitivity variants vs S1.
   The standard metric in GIS-MCDA sensitivity literature (Malczewski 2011;
   Feizizadeh & Blaschke 2014). Complements Jaccard top-decile.

2. V9: OFI 50/50 split (TX proximity 50%, road 50%) — same as V8 but for
   OFI internal weights. Closes the symmetrical gap: ESI weights tested (V8),
   OFI weights tested (V9).

Run with:
    ./gis_venv/bin/python3 step17_spearman_ofi5050.py
"""

import os, json, subprocess
import numpy as np
from scipy.stats import spearmanr

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
    tmp = tif + ".tmp17.raw"
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
    tmp_raw = path + ".tmp17.raw"
    tmp_vrt = path + ".tmp17.vrt"
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


# ── Part 1: Spearman ρ for all existing variant rasters ─────────────────────

print("\n=== Part 1: Spearman ρ for all sensitivity variants vs S1 ===")
print("(Standard metric per Malczewski 2011; Feizizadeh & Blaschke 2014)\n")

# Load S1 baseline
gric_s1 = read_raster(f"{RDIR}/gric_s1_baseline_1km.tif")
eligible = ~np.isnan(gric_s1)
s1_vals  = gric_s1[eligible]
print(f"  S1 eligible cells: {eligible.sum():,}")

# Variant rasters: file → label
VARIANTS = {
    # Sensitivity variants (V1–V8, best-effort file names)
    "gric_v1_tx_cap30km_1km.tif":           "V1  TX cap 30 km",
    "gric_v2_road_cap100km_1km.tif":         "V2  Road cap 100 km",
    "gric_v3_heat_included_1km.tif":         "V3  Heat included",
    "gric_v4_slope_included_1km.tif":        "V4  Slope included",
    "gric_v5_sfha5pct_1km.tif":              "V5  SFHA 5% threshold",
    "gric_v6_eji25_1km.tif":                 "V6  EJI penalty 25%",
    "gric_v7_eji75_1km.tif":                 "V7  EJI penalty 75%",
    "gric_v8_equal_esi_weights_1km.tif":     "V8  Equal ESI weights",
    # Scenario rasters
    "gric_s2_envfirst_1km.tif":              "S2  Env-first (70/30)",
    "gric_s3_devfirst_1km.tif":              "S3  Dev-first (30/70)",
    "gric_s4_commprot_1km.tif":              "S4  Community-protection",
    "gric_s5_conserv_1km.tif":              "S5  Conservation",
}

# Jaccard results from existing JSON (to print alongside)
json_path = f"{BASE}/00_ADMIN/scenario_robustness.json"
existing_jaccard = {}
if os.path.exists(json_path):
    with open(json_path) as f:
        rob = json.load(f)
    sc_map = {
        "S2": "S2", "S3": "S3", "S4": "S4", "S5": "S5",
        "V8_equal_ESI": "V8  Equal ESI weights",
    }
    for k, v in rob.get("scenarios", {}).items():
        existing_jaccard[k] = v.get("jaccard_vs_s1", None)

print(f"  {'Variant':<30}  {'Spearman ρ':>11}  {'Jaccard':>8}  {'Status':}")
print("  " + "-"*70)

spearman_results = {}
for fname, label in VARIANTS.items():
    fpath = f"{RDIR}/{fname}"
    if not os.path.exists(fpath):
        print(f"  {label:<30}  {'(file missing)':>11}")
        spearman_results[label] = None
        continue
    arr = read_raster(fpath)
    # Only cells valid in BOTH surfaces
    both = eligible & ~np.isnan(arr)
    v_s1  = gric_s1[both]
    v_var = arr[both]
    if len(v_s1) < 100:
        print(f"  {label:<30}  {'(too few cells)':>11}")
        continue
    rho, pval = spearmanr(v_s1, v_var)
    # Jaccard lookup
    jac_str = "—"
    for k, jval in existing_jaccard.items():
        if k in label or label.startswith(k[:2]):
            if jval is not None:
                jac_str = f"{jval:.3f}"
                break
    sig = "***" if pval < 0.001 else ("**" if pval < 0.01 else ("*" if pval < 0.05 else ""))
    print(f"  {label:<30}  {rho:>10.4f}  {jac_str:>8}  {sig}")
    spearman_results[label] = {"spearman_rho": round(float(rho), 4), "p_value": float(pval)}

# ── Part 2: V9 OFI 50/50 ────────────────────────────────────────────────────

print("\n=== Part 2: V9 — OFI internal weights 50/50 (TX=50%, road=50%) ===")
print("(Parallel test to V8; closes ESI/OFI symmetry gap in sensitivity)\n")

water_s  = read_raster(f"{RDIR}/water_stress_baseline_bws_suitability.tif")
wildfire = read_raster(f"{RDIR}/nri_wildfire_suitability_1km.tif")
flood    = read_raster(f"{RDIR}/nri_inland_flood_suitability_1km.tif")
tx230    = read_raster(f"{RDIR}/hifld_tx_230kV_proximity_1km.tif")
road     = read_raster(f"{RDIR}/tiger_roads_prisec_proximity_1km.tif")
print("  Rasters loaded.")

# ESI S1 (unchanged)
all_esi_v = (~np.isnan(water_s)) & (~np.isnan(wildfire)) & (~np.isnan(flood))
esi_s1 = (
    (3/7) * np.nan_to_num(water_s,  nan=0) +
    (2/7) * np.nan_to_num(wildfire, nan=0) +
    (2/7) * np.nan_to_num(flood,    nan=0)
)
esi_s1[~all_esi_v] = np.nan

# V9 OFI: 50/50 instead of 70/30
suit_tx   = np.clip(1.0 - tx230 / 100000.0, 0.0, 1.0); suit_tx[np.isnan(tx230)]  = np.nan
suit_road = np.clip(1.0 - road  /  30000.0, 0.0, 1.0); suit_road[np.isnan(road)] = np.nan
all_ofi_v = (~np.isnan(suit_tx)) & (~np.isnan(suit_road))

# Baseline OFI (70/30)
ofi_s1 = 0.70 * np.nan_to_num(suit_tx, nan=0) + 0.30 * np.nan_to_num(suit_road, nan=0)
ofi_s1[~all_ofi_v] = np.nan

# V9 OFI (50/50)
ofi_v9 = 0.50 * np.nan_to_num(suit_tx, nan=0) + 0.50 * np.nan_to_num(suit_road, nan=0)
ofi_v9[~all_ofi_v] = np.nan

print(f"  OFI S1 (70/30)  mean: {np.nanmean(ofi_s1[eligible]):.4f}  std: {np.nanstd(ofi_s1[eligible]):.4f}")
print(f"  OFI V9 (50/50)  mean: {np.nanmean(ofi_v9[eligible]):.4f}  std: {np.nanstd(ofi_v9[eligible]):.4f}")
print(f"  Max OFI abs diff: {np.nanmax(np.abs(ofi_v9 - ofi_s1)):.4f}")

# GRIC V9: ESI S1 weights, OFI V9, 50/50 macro-split
all_v    = (~np.isnan(esi_s1)) & (~np.isnan(ofi_v9))
gric_v9  = 0.50 * np.nan_to_num(esi_s1, nan=0) + 0.50 * np.nan_to_num(ofi_v9, nan=0)
gric_v9[~all_v] = np.nan

flat_v9 = gric_v9[eligible & ~np.isnan(gric_v9)]
flat_s1 = gric_s1[eligible & ~np.isnan(gric_s1)]
print(f"\n  V9 cells: {len(flat_v9):,}  mean: {np.mean(flat_v9):.4f}  p90: {np.percentile(flat_v9, 90):.4f}")
print(f"  S1 cells: {len(flat_s1):,}  mean: {np.mean(flat_s1):.4f}  p90: {np.percentile(flat_s1, 90):.4f}")

write_raster(gric_v9, f"{RDIR}/gric_v9_ofi5050_1km.tif")

# Jaccard
q90_s1 = np.percentile(flat_s1, 90)
q90_v9 = np.percentile(flat_v9, 90)
top_s1 = (gric_s1 >= q90_s1) & eligible & ~np.isnan(gric_s1)
top_v9 = (gric_v9 >= q90_v9) & eligible & ~np.isnan(gric_v9)
inter  = int(np.sum(top_s1 & top_v9))
union  = int(np.sum(top_s1 | top_v9))
j_v9   = inter / union if union > 0 else 0.0

# Spearman
both   = eligible & ~np.isnan(gric_v9)
rho_v9, pval_v9 = spearmanr(gric_s1[both], gric_v9[both])

print(f"\n  Jaccard (V9 vs S1)    : {j_v9:.3f}")
print(f"  Spearman ρ (V9 vs S1) : {rho_v9:.4f}  (p = {pval_v9:.2e})")

# State breakdown
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
    return m & eligible

print(f"\n  {'State':<6}  {'S1 share':>10}  {'V9 share':>10}  {'Δ':>8}")
print("  " + "-"*42)
for state, bbox in STATE_BBOX.items():
    sm    = bbox_to_mask(*bbox)
    n_elig = sm.sum()
    if n_elig == 0: continue
    s_s1  = np.sum(top_s1 & sm) / n_elig * 100
    s_v9  = np.sum(top_v9 & sm) / n_elig * 100
    print(f"  {state:<6}  {s_s1:>9.1f}%  {s_v9:>9.1f}%  {s_v9-s_s1:>+7.1f}%")

# Update JSON
if os.path.exists(json_path):
    with open(json_path) as f:
        rob = json.load(f)
else:
    rob = {"scenarios": {}}

rob["scenarios"]["V9_ofi5050"] = {
    "label": "V9 OFI equal weights (TX=50%, road=50%)",
    "jaccard_vs_s1": round(j_v9, 3),
    "spearman_rho_vs_s1": round(float(rho_v9), 4),
    "n_top_decile": int(top_v9.sum()),
    "p90_threshold": round(float(q90_v9), 4),
    "weights": {"tx230_pct": 0.50, "road_pct": 0.50},
}
rob["sensitivity_spearman"] = {k: v for k, v in spearman_results.items() if v is not None}

with open(json_path, "w") as f:
    json.dump(rob, f, indent=2)
print(f"\n  → scenario_robustness.json updated with V9 + Spearman results")

print("\n=== DONE ===")
print(f"\n  SUMMARY")
print(f"  V9 Jaccard  (OFI 50/50 vs S1) : {j_v9:.3f}")
print(f"  V9 Spearman (OFI 50/50 vs S1) : {rho_v9:.4f}")
print(f"  TX weight change: 70% → 50%  (Δ = -20pp)")
print(f"  Road weight change: 30% → 50%  (Δ = +20pp)")
