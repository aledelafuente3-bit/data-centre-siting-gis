#!/usr/bin/env python3
"""
Step 12 — GRIC Mode A composite + carbon module + confidence + sensitivity + validation
Run with: PROJ_LIB=".../share/proj" GDAL_DATA=".../share/gdal" python3 step12_gric_composite_analysis.py
"""
import os, sys, subprocess, struct, csv, math
import numpy as np

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RDIR = f"{BASE}/11_processed_layers/rasters"
VDIR = f"{BASE}/06_VALIDATION"
ADMIN = f"{BASE}/00_ADMIN"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"

os.environ.setdefault("PROJ_LIB", "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj")
os.environ.setdefault("GDAL_DATA", "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal")

try:
    from osgeo import gdal
    gdal.UseExceptions()
except ImportError:
    sys.exit("ERROR: osgeo.gdal not available. Run with QGIS Python.")

# Grid constants
NROWS, NCOLS = 2597, 4086
XMIN, YMAX = -2295000, 2907000
CELLSIZE = 1000
ND = -9999.0

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def read_band(path):
    """Return float32 array (NROWS, NCOLS) with NoData cells set to np.nan."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Cannot open: {path}")
    b = ds.GetRasterBand(1)
    nd = b.GetNoDataValue()
    arr = b.ReadAsArray().astype(np.float32)
    if nd is not None:
        arr[arr == nd] = np.nan
    return arr

def write_raster(arr, path, nodata=ND, dtype=np.float32):
    """Write numpy array to GeoTIFF via VRT (workaround for PROJ.db issue)."""
    arr_out = np.where(np.isnan(arr), nodata, arr).astype(dtype)
    tmp_raw = path.replace(".tif", "_raw.bin")
    arr_out.tofile(tmp_raw)

    dt_map = {np.float32: "Float32", np.int16: "Int16",
              np.uint8: "Byte", np.int32: "Int32"}
    gdt = dt_map.get(dtype, "Float32")
    vrt_path = tmp_raw.replace(".bin", ".vrt")
    vrt_xml = f"""<VRTDataset rasterXSize="{NCOLS}" rasterYSize="{NROWS}">
  <SRS>EPSG:5070</SRS>
  <GeoTransform>{XMIN}, {CELLSIZE}, 0, {YMAX}, 0, -{CELLSIZE}</GeoTransform>
  <VRTRasterBand dataType="{gdt}" band="1" subClass="VRTRawRasterBand">
    <NoDataValue>{nodata}</NoDataValue>
    <SourceFilename relativeToVRT="1">{os.path.basename(tmp_raw)}</SourceFilename>
    <ImageOffset>0</ImageOffset>
    <PixelOffset>{arr_out.itemsize}</PixelOffset>
    <LineOffset>{NCOLS * arr_out.itemsize}</LineOffset>
    <ByteOrder>LSB</ByteOrder>
  </VRTRasterBand>
</VRTDataset>"""
    with open(vrt_path, "w") as f:
        f.write(vrt_xml)

    env = os.environ.copy()
    subprocess.run([
        f"{GDAL_BIN}/gdal_translate",
        "-co", "COMPRESS=LZW", "-co", "TILED=YES",
        vrt_path, path
    ], check=True, env=env, capture_output=True)
    os.remove(tmp_raw)
    os.remove(vrt_path)
    print(f"  Written: {os.path.basename(path)}")

def stats(arr, label=""):
    """Print quick stats for a masked array (ignores nan)."""
    v = arr[~np.isnan(arr)]
    n = len(v)
    if n == 0:
        print(f"  {label}: ALL NaN")
        return
    print(f"  {label}: n={n:,}  min={v.min():.4f}  p25={np.percentile(v,25):.4f}  "
          f"p50={np.median(v):.4f}  p75={np.percentile(v,75):.4f}  max={v.max():.4f}  "
          f"mean={v.mean():.4f}")

def spearman_r(a, b):
    """Spearman ρ between two 1-D float arrays (no scipy needed)."""
    n = len(a)
    if n < 3:
        return float("nan")
    ra = a.argsort().argsort().astype(float)
    rb = b.argsort().argsort().astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    denom = np.sqrt((ra**2).sum() * (rb**2).sum())
    return float((ra * rb).sum() / (denom + 1e-12))

def xy_to_rowcol(x, y):
    """Convert EPSG:5070 coordinates to raster (row, col). Clamps to grid."""
    col = int((x - XMIN) / CELLSIZE)
    row = int((YMAX - y) / CELLSIZE)
    col = max(0, min(NCOLS - 1, col))
    row = max(0, min(NROWS - 1, row))
    return row, col

def jaccard_top_decile(base, variant, mask_valid):
    """Jaccard overlap of top-10% cells between base and variant (within valid mask)."""
    v_base = base[mask_valid]
    v_var  = variant[mask_valid]
    # Compute top-10% threshold separately for each
    thresh_base = np.nanpercentile(v_base, 90)
    thresh_var  = np.nanpercentile(v_var,  90)
    set_base = set(np.where(mask_valid & (base >= thresh_base))[0])  # flat indices
    set_var  = set(np.where(mask_valid & (variant >= thresh_var))[0])
    intersection = len(set_base & set_var)
    union = len(set_base | set_var)
    return intersection / union if union > 0 else 0.0

# For flat-index version (memory efficient)
def jaccard_flat(base_flat, var_flat, n_valid_flat):
    """Both inputs are 1D arrays of scores for valid cells only."""
    q90_b = np.nanpercentile(base_flat, 90)
    q90_v = np.nanpercentile(var_flat,  90)
    top_b = base_flat >= q90_b
    top_v = var_flat  >= q90_v
    inter = np.sum(top_b & top_v)
    union = np.sum(top_b | top_v)
    return float(inter / union) if union > 0 else 0.0

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 0 — LOAD RASTERS
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 0: Loading rasters ===")

R = {}
to_load = {
    # Hard exclusion
    "pad12":    f"{RDIR}/pad_us_gap12_exclusion_1km.tif",
    "water_wl": f"{RDIR}/pct_waterwetland_1km_EPSG5070.tif",
    "eligible": f"{RDIR}/pct_eligible_1km_EPSG5070.tif",
    "floodway": f"{RDIR}/nfhl_floodway_fraction_1km.tif",
    "sfha":     f"{RDIR}/nfhl_sfha_fraction_1km.tif",
    # ESI
    "water_s":  f"{RDIR}/water_stress_baseline_bws_suitability.tif",
    "wildfire": f"{RDIR}/nri_wildfire_suitability_1km.tif",
    "flood":    f"{RDIR}/nri_inland_flood_suitability_1km.tif",
    "heat":     f"{RDIR}/nexgddp_mean_days_gt35_2041_2060.tif",
    "slope":    f"{RDIR}/slope_pct_below8pct_1km.tif",
    # OFI
    "tx230":    f"{RDIR}/hifld_tx_230kV_proximity_1km.tif",
    "tx345":    f"{RDIR}/hifld_tx_345kV_proximity_1km.tif",
    "road":     f"{RDIR}/tiger_roads_prisec_proximity_1km.tif",
    "road_p":   f"{RDIR}/tiger_roads_primary_proximity_1km.tif",
    # Carbon
    "co2e_raw":  f"{RDIR}/carbon_current_co2e_raw.tif",
    "co2e_suit": f"{RDIR}/carbon_current_co2e_suitability.tif",
    "co2f_raw":  f"{RDIR}/carbon_future2040_aer_load_co2e_raw.tif",
    "co2f_suit": f"{RDIR}/carbon_future2040_aer_load_co2e_suit.tif",
    # QA/flags
    "saidi_flag":  f"{RDIR}/saidi_nodata_flag_1km.tif",
    "nfhl_qa":     f"{RDIR}/nfhl_coverage_qa_1km.tif",
    "eji_score":   f"{RDIR}/eji_2024_score_1km.tif",
    "eji_flag":    f"{RDIR}/eji_2024_flag_p75_1km.tif",
    # Mask
    "mask":     f"{RDIR}/mask_7states_1km_EPSG5070.tif",
}

for key, path in to_load.items():
    if not os.path.exists(path):
        print(f"  WARNING: Missing {key}: {path}")
        R[key] = None
    else:
        R[key] = read_band(path)
        print(f"  Loaded {key}: {path.split('/')[-1]}")

# Verify mask
mask7 = ~np.isnan(R["mask"])  # True = valid 7-state cell
print(f"\n  7-state valid cells: {mask7.sum():,}")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — HARD EXCLUSION MASK
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 1: Hard exclusion mask ===")

def build_excl(sfha_threshold=0.25):
    """Return boolean array: True = EXCLUDED."""
    excl = np.zeros((NROWS, NCOLS), dtype=bool)
    # E-1 PAD-US GAP 1+2
    if R["pad12"] is not None:
        excl |= (R["pad12"] == 1)
    # E-2 Water/wetland >= 50%
    if R["water_wl"] is not None:
        excl |= (R["water_wl"] >= 0.50)
    # E-3 eligible < 10%
    if R["eligible"] is not None:
        # NaN in eligible (outside mask) treated as excluded
        elig = R["eligible"].copy()
        elig[np.isnan(elig)] = 0.0
        excl |= (elig < 0.10)
    # E-4 floodway > 0
    if R["floodway"] is not None:
        fw = R["floodway"].copy(); fw[np.isnan(fw)] = 0.0
        excl |= (fw > 0)
    # E-5 SFHA >= threshold
    if R["sfha"] is not None:
        sfha = R["sfha"].copy(); sfha[np.isnan(sfha)] = 0.0
        excl |= (sfha >= sfha_threshold)
    # Also exclude cells outside the 7-state mask
    excl |= ~mask7
    return excl

excl_base = build_excl(sfha_threshold=0.25)
excl_tight = build_excl(sfha_threshold=0.05)

n_excl = excl_base.sum()
n_elig = mask7.sum() - n_excl
print(f"  Excluded cells (base): {n_excl:,}")
print(f"  Eligible cells (base): {n_elig:,}")
n_excl_tight = excl_tight.sum()
n_elig_tight = mask7.sum() - n_excl_tight
print(f"  Excluded cells (SFHA 5%): {n_excl_tight:,}  Eligible: {n_elig_tight:,}")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — GRIC S1 BASELINE (Mode A — carbon excluded)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 2: GRIC S1 baseline (Mode A) ===")

# OFI normalization (on-the-fly from raw proximity)
# 230kV TX: cap=100km
suit_tx = np.clip(1.0 - R["tx230"] / 100000.0, 0.0, 1.0)
suit_tx[np.isnan(R["tx230"])] = np.nan

# Road pri+sec: cap=30km
suit_road = np.clip(1.0 - R["road"] / 30000.0, 0.0, 1.0)
suit_road[np.isnan(R["road"])] = np.nan

# ESI (Mode A): water=3/7, wildfire=2/7, flood=2/7
w_water = 3/7; w_wild = 2/7; w_flood = 2/7  # sum=1.0

def make_esi_modeA(water, wildfire, flood, heat=None, heat_weight=0.0):
    """ESI score for Mode A. Optional heat layer with its own weight (renorms others)."""
    # Assemble layers, NaN where any layer is NaN or all are NaN
    layers = []
    if heat is not None and heat_weight > 0:
        # renorm non-heat to fill (1-heat_weight)
        scale = (1 - heat_weight)
        ww = w_water * scale; wwild = w_wild * scale; wfl = w_flood * scale
        suit_heat = np.clip(1.0 - heat / 130.0, 0.0, 1.0)
        suit_heat[np.isnan(heat)] = np.nan
        esi = (np.nan_to_num(ww * water, nan=0) +
               np.nan_to_num(wwild * wildfire, nan=0) +
               np.nan_to_num(wfl * flood, nan=0) +
               np.nan_to_num(heat_weight * suit_heat, nan=0))
        # count non-NaN contributors
        cnt = ((~np.isnan(water)).astype(float) +
               (~np.isnan(wildfire)).astype(float) +
               (~np.isnan(flood)).astype(float) +
               (~np.isnan(suit_heat)).astype(float))
        # if all 4 present just use weighted sum; if any missing set NaN
        all_valid = (~np.isnan(water)) & (~np.isnan(wildfire)) & (~np.isnan(flood)) & (~np.isnan(suit_heat))
        esi[~all_valid] = np.nan
    else:
        esi = (np.nan_to_num(w_water * water, nan=0) +
               np.nan_to_num(w_wild * wildfire, nan=0) +
               np.nan_to_num(w_flood * flood, nan=0))
        all_valid = (~np.isnan(water)) & (~np.isnan(wildfire)) & (~np.isnan(flood))
        esi[~all_valid] = np.nan
    return esi

def make_ofi(suit_tx_use, suit_road_use, slope_arr=None, w_tx=0.70, w_rd=0.30, w_sl=0.0):
    """OFI score. Optional slope layer."""
    if slope_arr is not None and w_sl > 0:
        scale = 1 - w_sl
        w_tx2 = w_tx * scale; w_rd2 = w_rd * scale
        ofi = (np.nan_to_num(w_tx2 * suit_tx_use, nan=0) +
               np.nan_to_num(w_rd2 * suit_road_use, nan=0) +
               np.nan_to_num(w_sl * slope_arr, nan=0))
        all_valid = (~np.isnan(suit_tx_use)) & (~np.isnan(suit_road_use)) & (~np.isnan(slope_arr))
        ofi[~all_valid] = np.nan
    else:
        ofi = (np.nan_to_num(w_tx * suit_tx_use, nan=0) +
               np.nan_to_num(w_rd * suit_road_use, nan=0))
        all_valid = (~np.isnan(suit_tx_use)) & (~np.isnan(suit_road_use))
        ofi[~all_valid] = np.nan
    return ofi

def make_gric(esi, ofi, excl, w_esi=0.50, w_ofi=0.50):
    """Composite: ESI×w + OFI×(1-w), NaN on excluded."""
    g = np.nan_to_num(w_esi * esi, nan=0) + np.nan_to_num(w_ofi * ofi, nan=0)
    all_v = (~np.isnan(esi)) & (~np.isnan(ofi))
    g[~all_v] = np.nan
    g[excl] = np.nan
    return g

esi_s1 = make_esi_modeA(R["water_s"], R["wildfire"], R["flood"])
ofi_s1 = make_ofi(suit_tx, suit_road)
gric_s1 = make_gric(esi_s1, ofi_s1, excl_base)

stats(gric_s1, "GRIC_S1")
write_raster(gric_s1, f"{RDIR}/gric_s1_baseline_1km.tif")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — GRS CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 3: GRS classification ===")

d230 = R["tx230"].copy(); d230[np.isnan(d230)] = 1e9
d345 = R["tx345"].copy(); d345[np.isnan(d345)] = 1e9

grs = np.zeros((NROWS, NCOLS), dtype=np.float32)
grs[mask7] = 1  # GRS-C default for all valid cells
grs[(d345 <= 50000) | (d230 <= 30000)] = 2  # GRS-B
grs[(d345 <= 25000) | (d230 <= 15000)] = 3  # GRS-A
grs[excl_base | ~mask7] = np.nan

stats(grs, "GRS")
for cls, lbl in [(3,"GRS-A"), (2,"GRS-B"), (1,"GRS-C")]:
    n = np.sum(grs == cls)
    print(f"    {lbl}: {n:,} cells")
write_raster(grs, f"{RDIR}/grs_class_1km.tif")

# GRS sensitivity: alternative thresholds
grs_thresholds = [
    ("15_25_km",  15000, 25000),  # tighter A: 15km/25km
    ("30_50_km",  30000, 50000),  # baseline (default above)
]
print("  GRS threshold sensitivity:")
for name, t230, t345 in grs_thresholds:
    gA = np.sum(mask7 & ~excl_base & ((d345 <= t345) | (d230 <= t230)))
    gB_25 = 50000; gB_230 = 30000
    gB = np.sum(mask7 & ~excl_base & ((d345 <= gB_25) | (d230 <= gB_230)) & ~((d345 <= t345) | (d230 <= t230)))
    print(f"    A≤{t230/1000:.0f}km(230) or ≤{t345/1000:.0f}km(345): GRS-A={gA:,} cells")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — CARBON MODULE
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 4: Carbon module ===")

# Delta map (descriptive only — not in GRIC)
# Note: different accounting bases — cannot difference-score in GRIC
co2e_curr = R["co2e_raw"]
co2e_fut  = R["co2f_raw"]
delta = co2e_fut - co2e_curr
delta[np.isnan(co2e_curr) | np.isnan(co2e_fut)] = np.nan
delta[~mask7] = np.nan
stats(delta, "ΔCarbon (future−current, g/kWh CO₂e)")
write_raster(delta, f"{RDIR}/carbon_delta_gkwh_1km.tif")

# Suitability tiers (5 classes: 0–0.2, 0.2–0.4, 0.4–0.6, 0.6–0.8, 0.8–1.0)
def suit_to_tier(suit_arr, excl):
    tier = np.full_like(suit_arr, np.nan)
    valid = ~np.isnan(suit_arr) & ~excl
    s = suit_arr[valid]
    t = np.zeros(len(s), dtype=np.float32)
    t[(s >= 0.0) & (s < 0.2)] = 1
    t[(s >= 0.2) & (s < 0.4)] = 2
    t[(s >= 0.4) & (s < 0.6)] = 3
    t[(s >= 0.6) & (s < 0.8)] = 4
    t[(s >= 0.8) & (s <= 1.0)] = 5
    tier[valid] = t
    return tier

tier_curr = suit_to_tier(R["co2e_suit"], excl_base)
stats(tier_curr, "Carbon_suit_current_tier")
write_raster(tier_curr, f"{RDIR}/carbon_suit_current_tier_1km.tif")

tier_fut = suit_to_tier(R["co2f_suit"], excl_base)
stats(tier_fut, "Carbon_suit_future_tier")
write_raster(tier_fut, f"{RDIR}/carbon_suit_future_tier_1km.tif")

# Tier counts
for arr, label in [(tier_curr, "Current"), (tier_fut, "Future")]:
    print(f"  {label} carbon tier counts:")
    for t in [1,2,3,4,5]:
        n = np.sum(arr == t)
        pct = 100 * n / n_elig if n_elig > 0 else 0
        print(f"    Tier {t}: {n:,} ({pct:.1f}%)")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — CONFIDENCE MAP
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 5: Composite confidence ===")

# 4 binary QA components (1=data present, 0=gap)
saidi_ok = np.where(np.isnan(R["saidi_flag"]), 0, R["saidi_flag"].astype(float))
nfhl_ok  = np.where(np.isnan(R["nfhl_qa"]),   0, R["nfhl_qa"].astype(float))
co2e_ok  = (~np.isnan(R["co2e_raw"])).astype(float)
eji_ok   = (~np.isnan(R["eji_score"])).astype(float)

confidence = (saidi_ok + nfhl_ok + co2e_ok + eji_ok) / 4.0
confidence[excl_base | ~mask7] = np.nan
stats(confidence, "Composite_confidence")

# Count cells by confidence tier
for lo, hi, label in [(0.76, 1.01, "Full (all 4 OK)"), (0.51, 0.76, "High (3/4)"),
                       (0.26, 0.51, "Moderate (2/4)"), (0.0, 0.26, "Low (≤1/4)")]:
    n = np.sum((confidence >= lo) & (confidence < hi))
    print(f"  {label}: {n:,} cells")

write_raster(confidence, f"{RDIR}/composite_confidence_1km.tif")

# τ=0.50 mask: flag cells below threshold
tau_mask = np.full_like(confidence, np.nan)
tau_mask[~np.isnan(confidence)] = (confidence[~np.isnan(confidence)] < 0.50).astype(float)
n_low = int(np.nansum(tau_mask))
pct_low = 100 * n_low / n_elig if n_elig > 0 else 0
print(f"  Cells with confidence < 0.50 (τ mask): {n_low:,} ({pct_low:.1f}% of eligible)")
write_raster(tau_mask, f"{RDIR}/composite_confidence_mask_tau50_1km.tif")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6 — EJI BOUNDED DOWN-RANK
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 6: EJI bounded down-rank ===")

EJI_P75 = 0.691  # within-7-state P75 threshold from weighting framework

def eji_adjusted_gric(base_gric, penalty):
    eji = R["eji_score"].copy()
    eji[np.isnan(eji)] = 0.0
    norm_eji = np.clip(eji / EJI_P75, 0.0, 1.0)
    ce_factor = 1.0 - penalty * norm_eji
    adj = base_gric * ce_factor
    adj[np.isnan(base_gric)] = np.nan
    adj[excl_base] = np.nan
    return adj, ce_factor

gric_eji50, ce50 = eji_adjusted_gric(gric_s1, 0.50)
stats(gric_eji50, "GRIC_EJI_bounded(penalty=0.50)")
write_raster(gric_eji50, f"{RDIR}/gric_s1_eji_bounded_1km.tif")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7 — SENSITIVITY ANALYSIS (7 variants)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 7: Sensitivity analysis ===")

# Baseline flat arrays for Spearman/Jaccard
valid_mask = ~np.isnan(gric_s1)
base_flat = gric_s1[valid_mask]

sensitivity_results = []

def run_variant(name, gric_var, excl_var=excl_base):
    vm = ~np.isnan(gric_var)
    var_flat = gric_var[vm]
    base_flat_v = gric_s1[vm]
    rho = spearman_r(base_flat_v, var_flat)
    jac = jaccard_flat(base_flat_v, var_flat, len(var_flat))
    n_elig_v = vm.sum()
    print(f"  {name}: n_elig={n_elig_v:,}  ρ={rho:.4f}  Jaccard_top10%={jac:.4f}")
    return {"variant": name, "n_eligible": n_elig_v, "spearman_rho": round(rho, 4),
            "jaccard_top10pct": round(jac, 4)}

# V1: TX cap 30km
suit_tx_30 = np.clip(1.0 - R["tx230"] / 30000.0, 0.0, 1.0)
suit_tx_30[np.isnan(R["tx230"])] = np.nan
ofi_v1 = make_ofi(suit_tx_30, suit_road)
gric_v1 = make_gric(esi_s1, ofi_v1, excl_base)
write_raster(gric_v1, f"{RDIR}/gric_sensit_tx_cap30km_1km.tif")
sensitivity_results.append(run_variant("V1_TX_cap30km", gric_v1))

# V2: Road cap 100km
suit_road_100 = np.clip(1.0 - R["road"] / 100000.0, 0.0, 1.0)
suit_road_100[np.isnan(R["road"])] = np.nan
ofi_v2 = make_ofi(suit_tx, suit_road_100)
gric_v2 = make_gric(esi_s1, ofi_v2, excl_base)
write_raster(gric_v2, f"{RDIR}/gric_sensit_road_cap100km_1km.tif")
sensitivity_results.append(run_variant("V2_Road_cap100km", gric_v2))

# V3: Heat days included (ESI heat_weight=20/90 of ESI, total ESI budget still 50%)
esi_v3 = make_esi_modeA(R["water_s"], R["wildfire"], R["flood"], R["heat"], heat_weight=2/9)
gric_v3 = make_gric(esi_v3, ofi_s1, excl_base)
write_raster(gric_v3, f"{RDIR}/gric_sensit_heat_included_1km.tif")
sensitivity_results.append(run_variant("V3_Heat_included", gric_v3))

# V4: Slope included in OFI (TX 60%, road 25%, slope 15%)
slope = R["slope"]
slope_clean = slope.copy(); slope_clean[np.isnan(slope_clean)] = np.nan
ofi_v4 = make_ofi(suit_tx, suit_road, slope_arr=slope_clean, w_tx=0.70, w_rd=0.30, w_sl=0.15)
# Renorm: effective = TX*0.85*0.70+road*0.85*0.30+slope*0.15 = TX*0.595+road*0.255+slope*0.15
# Simplify: use make_ofi with w_tx=0.595, w_rd=0.255, w_sl=0.15 (sum=1.0)
ofi_v4 = make_ofi(suit_tx, suit_road, slope_arr=slope_clean, w_tx=0.595, w_rd=0.255, w_sl=0.15)
gric_v4 = make_gric(esi_s1, ofi_v4, excl_base)
write_raster(gric_v4, f"{RDIR}/gric_sensit_slope_included_1km.tif")
sensitivity_results.append(run_variant("V4_Slope_included", gric_v4))

# V5: SFHA threshold = 5%
gric_v5 = make_gric(esi_s1, ofi_s1, excl_tight)
write_raster(gric_v5, f"{RDIR}/gric_sensit_sfha_5pct_1km.tif")
sensitivity_results.append(run_variant("V5_SFHA_5pct", gric_v5))

# V6: EJI penalty = 0.25
gric_v6, _ = eji_adjusted_gric(gric_s1, 0.25)
write_raster(gric_v6, f"{RDIR}/gric_sensit_eji_pen25_1km.tif")
sensitivity_results.append(run_variant("V6_EJI_pen025", gric_v6))

# V7: EJI penalty = 0.75
gric_v7, _ = eji_adjusted_gric(gric_s1, 0.75)
write_raster(gric_v7, f"{RDIR}/gric_sensit_eji_pen75_1km.tif")
sensitivity_results.append(run_variant("V7_EJI_pen075", gric_v7))

# Write sensitivity CSV
sens_csv = f"{VDIR}/extracted_scores/sensitivity_results.csv"
with open(sens_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["variant","n_eligible","spearman_rho","jaccard_top10pct"])
    w.writeheader(); w.writerows(sensitivity_results)
print(f"\n  Sensitivity results → {sens_csv}")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 8 — VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Stage 8: Validation ===")

# Load DC scores CSV
dc_csv = f"{VDIR}/extracted_scores/data_center_scores.csv"
dc_rows = []
with open(dc_csv) as f:
    reader = csv.DictReader(f)
    for row in reader:
        dc_rows.append(row)
print(f"  Loaded {len(dc_rows)} DC points from CSV")

# Extract GRIC_S1 at each DC point
dc_gric = []
for row in dc_rows:
    try:
        x = float(row["x_5070"]); y = float(row["y_5070"])
        r, c = xy_to_rowcol(x, y)
        g = gric_s1[r, c]
        state = row.get("state","?")
        dc_gric.append({
            "name": row["name"], "state": state, "city": row.get("city",""),
            "x_5070": x, "y_5070": y,
            "gric_s1": float("nan") if np.isnan(g) else float(g),
            "tx230_prox_m": float(row.get("tx_230kV_prox_m", "nan")),
            "water_suit": float(row.get("water_suit", "nan")),
            "wildfire_score": float(row.get("wildfire_score", "nan")),
            "flood_score": float(row.get("flood_score", "nan")),
            # OFI suitability (recompute from proximity)
            "suit_tx": max(0, 1 - float(row.get("tx_230kV_prox_m","0"))/100000),
            "suit_road": max(0, 1 - float(row.get("tx_230kV_prox_m","0"))/30000),  # use TX as proxy until road extracted
        })
    except (ValueError, KeyError):
        pass

# Also extract actual road proximity at DC points
road_arr = R["road"]
for rec in dc_gric:
    x, y = rec["x_5070"], rec["y_5070"]
    r, c = xy_to_rowcol(x, y)
    rd = road_arr[r, c] if road_arr is not None and not np.isnan(road_arr[r,c]) else float("nan")
    rec["road_prox_m"] = float(rd)
    rec["suit_road"] = max(0, 1 - rd/30000) if not math.isnan(rd) else float("nan")

# Compute on-the-fly GRIC at DC points (for validation consistency)
for rec in dc_gric:
    esi_dc = (3/7 * rec.get("water_suit",0) + 2/7 * (rec.get("wildfire_score",0)/100) +
              2/7 * (rec.get("flood_score",0)/100)) if not math.isnan(rec.get("water_suit",float("nan"))) else float("nan")
    ofi_dc = (0.70 * rec.get("suit_tx",0) + 0.30 * rec.get("suit_road",0)) if not math.isnan(rec.get("suit_road",float("nan"))) else float("nan")
    if not math.isnan(esi_dc) and not math.isnan(ofi_dc):
        rec["gric_calc"] = 0.5 * esi_dc + 0.5 * ofi_dc
    else:
        rec["gric_calc"] = float("nan")

# Save DC GRIC scores
dc_gric_csv = f"{VDIR}/extracted_scores/gric_s1_dc_scores.csv"
with open(dc_gric_csv, "w", newline="") as f:
    fields = ["name","state","city","x_5070","y_5070","gric_s1","gric_calc",
              "suit_tx","suit_road","road_prox_m","tx230_prox_m","water_suit"]
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader(); w.writerows(dc_gric)
print(f"  DC GRIC scores → {dc_gric_csv}")

# Filter to non-excluded DCs
valid_dc = [r for r in dc_gric if not math.isnan(r["gric_s1"])]
excl_dc  = [r for r in dc_gric if math.isnan(r["gric_s1"])]
print(f"  Valid DC points (not excluded): {len(valid_dc)}")
print(f"  Excluded DC points: {len(excl_dc)}")

# ── Metric 1: Capture rates ──
gric_vals = gric_s1[valid_mask]
p75 = float(np.nanpercentile(gric_vals, 75))
p90 = float(np.nanpercentile(gric_vals, 90))
p50 = float(np.nanpercentile(gric_vals, 50))

dc_gric_vals = [r["gric_s1"] for r in valid_dc]
cap10 = sum(g >= p90 for g in dc_gric_vals) / len(dc_gric_vals) if dc_gric_vals else 0
cap25 = sum(g >= p75 for g in dc_gric_vals) / len(dc_gric_vals) if dc_gric_vals else 0
cap50 = sum(g >= p50 for g in dc_gric_vals) / len(dc_gric_vals) if dc_gric_vals else 0
print(f"\n  CAPTURE RATES:")
print(f"    Top 10% (GRIC ≥ {p90:.3f}): {cap10*100:.1f}% of DCs")
print(f"    Top 25% (GRIC ≥ {p75:.3f}): {cap25*100:.1f}% of DCs")
print(f"    Top 50% (GRIC ≥ {p50:.3f}): {cap50*100:.1f}% of DCs")

# ── Metric 2: Distance to top-zone ──
print("\n  DISTANCE TO TOP-ZONE (top-25% GRIC cells):")
# Get top-25% cell row/col
top25_mask = (gric_s1 >= p75) & (~np.isnan(gric_s1))
top25_rows, top25_cols = np.where(top25_mask)
top25_x = XMIN + top25_cols * CELLSIZE + CELLSIZE/2
top25_y = YMAX - top25_rows * CELLSIZE - CELLSIZE/2
top25_pts = np.column_stack([top25_x, top25_y])
print(f"    Top-25% cells: {len(top25_rows):,}")

# For each DC, compute distance to nearest top-25% cell in chunks
def min_dist_to_set(dc_x, dc_y, pts_xy, chunk=200000):
    """Compute minimum Euclidean distance from (dc_x, dc_y) to any point in pts_xy."""
    min_d2 = np.inf
    n = len(pts_xy)
    for i in range(0, n, chunk):
        seg = pts_xy[i:i+chunk]
        d2 = ((seg[:,0] - dc_x)**2 + (seg[:,1] - dc_y)**2).min()
        if d2 < min_d2:
            min_d2 = d2
    return math.sqrt(min_d2) / 1000  # km

dists_km = []
for rec in valid_dc:
    d = min_dist_to_set(rec["x_5070"], rec["y_5070"], top25_pts)
    dists_km.append(d)
    rec["dist_to_top25_km"] = d

dists_arr = np.array(dists_km)
print(f"    Mean distance: {np.mean(dists_arr):.2f} km")
print(f"    Median: {np.median(dists_arr):.2f} km")
print(f"    P75: {np.percentile(dists_arr,75):.2f} km")
print(f"    P95: {np.percentile(dists_arr,95):.2f} km")
print(f"    Max: {np.max(dists_arr):.2f} km")
print(f"    DCs within 10 km of top-zone: {(dists_arr<=10).sum()} ({100*(dists_arr<=10).mean():.1f}%)")
print(f"    DCs within 50 km of top-zone: {(dists_arr<=50).sum()} ({100*(dists_arr<=50).mean():.1f}%)")

# ── Metric 3: State-level Spearman ρ ──
print("\n  STATE-LEVEL RANK AGREEMENT:")
# State DC counts
state_dc_count = {}
for rec in valid_dc:
    s = rec["state"]
    state_dc_count[s] = state_dc_count.get(s, 0) + 1

# State mean GRIC — use bounding boxes (approximate)
STATE_BOUNDS = {
    "AZ": (-2295000, -1750000, 310000, 770000),    # xmin, xmax, ymin, ymax in EPSG:5070
    "IL": (-250000,  400000,  1100000, 1900000),
    "IA": (-700000,  100000,  1350000, 1900000),
    "OR": (-2200000,-1400000, 1500000, 2100000),
    "TX": (-1400000, -350000,  500000, 1350000),
    "VA": (300000,   900000,  1050000, 1500000),
    "WV": (200000,   750000,   950000, 1350000),
}
rows_g, cols_g = np.mgrid[0:NROWS, 0:NCOLS]
x_g = XMIN + cols_g * CELLSIZE + CELLSIZE/2
y_g = YMAX - rows_g * CELLSIZE - CELLSIZE/2

state_gric_mean = {}
for state, (xlo, xhi, ylo, yhi) in STATE_BOUNDS.items():
    state_cells = (x_g >= xlo) & (x_g <= xhi) & (y_g >= ylo) & (y_g <= yhi) & (~np.isnan(gric_s1))
    v = gric_s1[state_cells]
    if len(v) > 0:
        state_gric_mean[state] = float(np.mean(v))

states_common = sorted(set(state_dc_count.keys()) & set(state_gric_mean.keys()))
dc_counts = np.array([state_dc_count.get(s, 0) for s in states_common], dtype=float)
gric_means = np.array([state_gric_mean.get(s, 0) for s in states_common], dtype=float)
rho_state = spearman_r(gric_means, dc_counts)
print(f"  State-level Spearman ρ (GRIC mean vs DC density): {rho_state:.4f} (n={len(states_common)} states)")
for s, g, d in zip(states_common, gric_means, dc_counts):
    print(f"    {s}: mean_gric={g:.3f}, n_dc={int(d)}")

# ── Metric 4: Leave-one-state-out capture rates ──
print("\n  LEAVE-ONE-STATE-OUT CAPTURE RATES:")
loso_results = {}
for held_state in ["AZ", "TX", "IL"]:
    if held_state not in STATE_BOUNDS:
        continue
    xlo, xhi, ylo, yhi = STATE_BOUNDS[held_state]
    # Define held-out state cells in raster
    in_held = (x_g >= xlo) & (x_g <= xhi) & (y_g >= ylo) & (y_g <= yhi)
    # Threshold from remaining 6 states only
    gric_other = gric_s1.copy()
    gric_other[in_held] = np.nan
    other_valid = ~np.isnan(gric_other)
    p75_other = float(np.nanpercentile(gric_other[other_valid], 75))
    # DC points in held state
    held_dcs = [r for r in valid_dc if r["state"] == held_state]
    if not held_dcs:
        print(f"    {held_state}: no valid DCs"); continue
    capture = sum(r["gric_s1"] >= p75_other for r in held_dcs) / len(held_dcs)
    loso_results[held_state] = {"threshold": p75_other, "n_dc": len(held_dcs),
                                  "capture_rate": capture}
    print(f"    {held_state}: {len(held_dcs)} DCs, threshold={p75_other:.3f}, capture_rate={capture*100:.1f}%")

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== All stages complete ===")
print(f"\nGRIC S1 baseline: {n_elig:,} eligible cells")
print(f"Capture rates — top10%:{cap10*100:.1f}%  top25%:{cap25*100:.1f}%  top50%:{cap50*100:.1f}%")
print(f"State Spearman ρ: {rho_state:.4f}")
print(f"Sensitivity results saved to: {sens_csv}")
print("All rasters written to:", RDIR)

# Save summary results dict for use in documentation
import json
summary = {
    "n_eligible_base": int(n_elig),
    "n_excluded_base": int(n_excl),
    "n_eligible_sfha5pct": int(n_elig_tight),
    "gric_s1_stats": {
        "p25": float(np.nanpercentile(gric_vals, 25)),
        "p50": float(np.nanpercentile(gric_vals, 50)),
        "p75": float(p75),
        "p90": float(p90),
        "mean": float(np.nanmean(gric_vals)),
    },
    "capture_rates": {"top10": cap10, "top25": cap25, "top50": cap50},
    "n_valid_dc": len(valid_dc),
    "n_excluded_dc": len(excl_dc),
    "dist_to_top25_km": {
        "mean": float(np.mean(dists_arr)), "median": float(np.median(dists_arr)),
        "p75": float(np.percentile(dists_arr,75)), "p95": float(np.percentile(dists_arr,95)),
        "within_10km_pct": float(100*(dists_arr<=10).mean()),
        "within_50km_pct": float(100*(dists_arr<=50).mean()),
    },
    "state_spearman_rho": float(rho_state),
    "loso": {s: {"n_dc": v["n_dc"], "capture_rate": v["capture_rate"], "threshold": v["threshold"]}
             for s, v in loso_results.items()},
    "sensitivity_results": sensitivity_results,
    "confidence_tau50_n_cells": int(n_low),
    "confidence_tau50_pct": float(pct_low),
    "carbon_tier_curr": {str(t): int(np.sum(tier_curr == t)) for t in [1,2,3,4,5]},
    "carbon_tier_fut": {str(t): int(np.sum(tier_fut == t)) for t in [1,2,3,4,5]},
    "grs_counts": {
        "GRS-A": int(np.sum(grs == 3)), "GRS-B": int(np.sum(grs == 2)),
        "GRS-C": int(np.sum(grs == 1)),
    },
}
summary_path = f"{ADMIN}/gric_analysis_summary.json"
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)
print(f"\nSummary JSON → {summary_path}")
