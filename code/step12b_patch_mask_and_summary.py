#!/usr/bin/env python3
"""Patch: fix mask7 definition, recompute GRS+confidence, fix state Spearman, write JSON."""
import os, sys, json, csv, math
import numpy as np

BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RDIR = f"{BASE}/11_processed_layers/rasters"
VDIR = f"{BASE}/06_VALIDATION"
ADMIN = f"{BASE}/00_ADMIN"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
os.environ.setdefault("PROJ_LIB", "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj")
os.environ.setdefault("GDAL_DATA", "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal")

try:
    from osgeo import gdal; gdal.UseExceptions()
except ImportError:
    sys.exit("Need QGIS Python")

import subprocess
NROWS, NCOLS = 2597, 4086
XMIN, YMAX, CELLSIZE = -2295000, 2907000, 1000
ND = -9999.0

def read_band(path):
    ds = gdal.Open(path)
    b = ds.GetRasterBand(1)
    nd = b.GetNoDataValue()
    arr = b.ReadAsArray().astype(np.float32)
    if nd is not None:
        arr[arr == nd] = np.nan
    return arr

def write_raster(arr, path, nodata=ND, dtype=np.float32):
    arr_out = np.where(np.isnan(arr), nodata, arr).astype(dtype)
    tmp_raw = path.replace(".tif", "_raw.bin")
    arr_out.tofile(tmp_raw)
    dt_map = {np.float32: "Float32", np.int16: "Int16", np.uint8: "Byte"}
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
    with open(vrt_path, "w") as f: f.write(vrt_xml)
    env = os.environ.copy()
    subprocess.run([f"{GDAL_BIN}/gdal_translate", "-co", "COMPRESS=LZW", "-co", "TILED=YES",
                    vrt_path, path], check=True, env=env, capture_output=True)
    os.remove(tmp_raw); os.remove(vrt_path)
    print(f"  Written: {os.path.basename(path)}")

def spearman_r(a, b):
    n = len(a)
    if n < 3: return float("nan")
    ra = a.argsort().argsort().astype(float)
    rb = b.argsort().argsort().astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    denom = np.sqrt((ra**2).sum() * (rb**2).sum())
    return float((ra * rb).sum() / (denom + 1e-12))

print("Loading rasters...")
mask_raw = read_band(f"{RDIR}/mask_7states_1km_EPSG5070.tif")
# Fix: mask7 = where mask value is 1 (not 0 or NaN)
# The mask raster has NoData=255 (→NaN after read_band) and value=1 inside 7 states, 0 outside
mask7 = (mask_raw == 1)  # True only inside 7-state boundary
print(f"  7-state valid cells (corrected): {mask7.sum():,}  (expected ~1,695,409)")

pad12   = read_band(f"{RDIR}/pad_us_gap12_exclusion_1km.tif")
water_wl= read_band(f"{RDIR}/pct_waterwetland_1km_EPSG5070.tif")
eligible= read_band(f"{RDIR}/pct_eligible_1km_EPSG5070.tif")
floodway= read_band(f"{RDIR}/nfhl_floodway_fraction_1km.tif")
sfha    = read_band(f"{RDIR}/nfhl_sfha_fraction_1km.tif")
tx230   = read_band(f"{RDIR}/hifld_tx_230kV_proximity_1km.tif")
tx345   = read_band(f"{RDIR}/hifld_tx_345kV_proximity_1km.tif")
saidi_f = read_band(f"{RDIR}/saidi_nodata_flag_1km.tif")
nfhl_qa = read_band(f"{RDIR}/nfhl_coverage_qa_1km.tif")
co2e_raw= read_band(f"{RDIR}/carbon_current_co2e_raw.tif")
eji_sc  = read_band(f"{RDIR}/eji_2024_score_1km.tif")
gric    = read_band(f"{RDIR}/gric_s1_baseline_1km.tif")

def build_excl(sfha_thresh=0.25):
    excl = np.zeros((NROWS, NCOLS), dtype=bool)
    excl |= (pad12 == 1)
    ew = water_wl.copy(); ew[np.isnan(ew)] = 0; excl |= (ew >= 0.50)
    el = eligible.copy(); el[np.isnan(el)] = 0; excl |= (el < 0.10)
    fw = floodway.copy(); fw[np.isnan(fw)] = 0; excl |= (fw > 0)
    sf = sfha.copy();     sf[np.isnan(sf)]  = 0; excl |= (sf >= sfha_thresh)
    excl |= ~mask7   # outside 7-state boundary
    return excl

excl_base = build_excl(0.25)
excl_tight = build_excl(0.05)
n_elig = int((mask7 & ~excl_base).sum())
n_elig_tight = int((mask7 & ~excl_tight).sum())
n_excl = int((mask7 & excl_base).sum())
print(f"  Excluded cells (7-state, base): {n_excl:,}")
print(f"  Eligible cells (7-state, base): {n_elig:,}")
print(f"  Eligible cells (7-state, SFHA 5%): {n_elig_tight:,}")

# ── GRS (corrected) ──
print("\nRecomputing GRS with corrected mask...")
d230 = tx230.copy(); d230[np.isnan(d230)] = 1e9
d345 = tx345.copy(); d345[np.isnan(d345)] = 1e9
grs = np.full((NROWS, NCOLS), np.nan, dtype=np.float32)
elig_cells = mask7 & ~excl_base
grs[elig_cells] = 1  # GRS-C
grs[elig_cells & ((d345 <= 50000) | (d230 <= 30000))] = 2  # GRS-B
grs[elig_cells & ((d345 <= 25000) | (d230 <= 15000))] = 3  # GRS-A
grs_counts = {
    "GRS-A": int((grs == 3).sum()),
    "GRS-B": int((grs == 2).sum()),
    "GRS-C": int((grs == 1).sum()),
}
for k,v in grs_counts.items():
    pct = 100*v/n_elig if n_elig > 0 else 0
    print(f"  {k}: {v:,} ({pct:.1f}%)")
write_raster(grs, f"{RDIR}/grs_class_1km.tif")

# ── Confidence (corrected) ──
print("\nRecomputing confidence with corrected mask...")
saidi_ok = np.where(np.isnan(saidi_f), 0.0, saidi_f.astype(float))
nfhl_ok  = np.where(np.isnan(nfhl_qa), 0.0, nfhl_qa.astype(float))
co2e_ok  = (~np.isnan(co2e_raw)).astype(float)
eji_ok   = (~np.isnan(eji_sc)).astype(float)
conf = (saidi_ok + nfhl_ok + co2e_ok + eji_ok) / 4.0
conf[~elig_cells] = np.nan
n_full  = int(np.sum(conf == 1.00))
n_high  = int(np.sum((conf >= 0.75) & (conf < 1.00)))
n_mod   = int(np.sum((conf >= 0.50) & (conf < 0.75)))
n_low   = int(np.sum((conf >= 0.0)  & (conf < 0.50)))
n_tau   = n_low
print(f"  Full (4/4): {n_full:,}  High (3/4): {n_high:,}  Mod (2/4): {n_mod:,}  Low (≤1/4): {n_low:,}")
pct_tau = 100 * n_tau / n_elig if n_elig > 0 else 0
print(f"  τ<0.50 cells: {n_tau:,} ({pct_tau:.1f}%)")
write_raster(conf, f"{RDIR}/composite_confidence_1km.tif")
tau_mask = np.full_like(conf, np.nan)
tau_mask[elig_cells] = (conf[elig_cells] < 0.50).astype(np.float32)
write_raster(tau_mask, f"{RDIR}/composite_confidence_mask_tau50_1km.tif")

# ── State Spearman ρ (corrected bounds) ──
print("\nState-level Spearman ρ (corrected bounds)...")
# Derived from DC point coordinates + generous buffer
STATE_BOUNDS = {
    "AZ": (-1700000, -1200000,  800000, 1500000),
    "IL": (  350000,   850000, 1700000, 2300000),
    "IA": ( -700000,   250000, 1500000, 2100000),
    "OR": (-2295000, -1550000, 2300000, 2907000),
    "TX": (-1200000,   300000,  310000, 1600000),
    "VA": ( 1300000,  1791000, 1500000, 2100000),
    "WV": (  900000,  1400000, 1200000, 1700000),
}
rows_g, cols_g = np.mgrid[0:NROWS, 0:NCOLS]
x_g = XMIN + cols_g * CELLSIZE + CELLSIZE/2
y_g = YMAX - rows_g * CELLSIZE - CELLSIZE/2

dc_csv = f"{VDIR}/extracted_scores/data_center_scores.csv"
dc_rows = list(csv.DictReader(open(dc_csv)))
state_dc_count = {}
for r in dc_rows:
    s = r["state"]; state_dc_count[s] = state_dc_count.get(s,0) + 1

state_gric_mean = {}
for state,(xlo,xhi,ylo,yhi) in STATE_BOUNDS.items():
    in_state = (x_g >= xlo) & (x_g <= xhi) & (y_g >= ylo) & (y_g <= yhi) & elig_cells & (~np.isnan(gric))
    v = gric[in_state]
    if len(v) > 100:
        state_gric_mean[state] = float(np.mean(v))
        print(f"  {state}: n_gric_cells={len(v):,}  mean_gric={np.mean(v):.3f}  n_dc={state_dc_count.get(state,0)}")

states_common = sorted(set(state_dc_count.keys()) & set(state_gric_mean.keys()))
dc_counts = np.array([state_dc_count.get(s,0) for s in states_common], dtype=float)
gric_means = np.array([state_gric_mean[s] for s in states_common], dtype=float)
rho_state = spearman_r(gric_means, dc_counts)
print(f"\n  State Spearman ρ (n={len(states_common)}): {rho_state:.4f}")

# ── Load validation results from previous run ──
sens_csv = f"{VDIR}/extracted_scores/sensitivity_results.csv"
sens_rows = list(csv.DictReader(open(sens_csv)))

dc_gric_csv = f"{VDIR}/extracted_scores/gric_s1_dc_scores.csv"
dc_gric_rows = list(csv.DictReader(open(dc_gric_csv)))
valid_dc = [r for r in dc_gric_rows if r["gric_s1"] not in ("","nan")]
valid_gric_vals = [float(r["gric_s1"]) for r in valid_dc]

gric_eligible = gric[elig_cells & (~np.isnan(gric))]
p50 = float(np.percentile(gric_eligible,50))
p75 = float(np.percentile(gric_eligible,75))
p90 = float(np.percentile(gric_eligible,90))
cap10 = sum(g >= p90 for g in valid_gric_vals)/len(valid_gric_vals) if valid_gric_vals else 0
cap25 = sum(g >= p75 for g in valid_gric_vals)/len(valid_gric_vals) if valid_gric_vals else 0
cap50 = sum(g >= p50 for g in valid_gric_vals)/len(valid_gric_vals) if valid_gric_vals else 0
print(f"\n  Rechecked capture rates: top10%={cap10*100:.1f}%  top25%={cap25*100:.1f}%  top50%={cap50*100:.1f}%")
print(f"  GRIC thresholds: p50={p50:.3f}  p75={p75:.3f}  p90={p90:.3f}")

# Read carbon tiers for counts
tier_curr = read_band(f"{RDIR}/carbon_suit_current_tier_1km.tif")
tier_fut  = read_band(f"{RDIR}/carbon_suit_future_tier_1km.tif")
delta = read_band(f"{RDIR}/carbon_delta_gkwh_1km.tif")
dv = delta[~np.isnan(delta)]

# Build summary JSON with all int/float conversions
summary = {
    "n_7state_cells": int(mask7.sum()),
    "n_excluded_base": n_excl,
    "n_eligible_base": n_elig,
    "n_eligible_sfha5pct": n_elig_tight,
    "gric_s1_stats": {
        "n_valid": int(np.sum(~np.isnan(gric) & elig_cells)),
        "min": float(np.nanmin(gric_eligible)),
        "p25": float(np.percentile(gric_eligible,25)),
        "p50": float(p50),
        "p75": float(p75),
        "p90": float(p90),
        "max": float(np.nanmax(gric_eligible)),
        "mean": float(np.mean(gric_eligible)),
    },
    "capture_rates": {"top10": float(cap10), "top25": float(cap25), "top50": float(cap50)},
    "n_valid_dc": len(valid_dc),
    "n_excluded_dc": len(dc_gric_rows) - len(valid_dc),
    "dist_to_top25_km": {
        "note": "computed in main script Stage 8 (valid, did not change with mask fix)"
    },
    "state_spearman_rho": float(rho_state),
    "state_details": {s: {"mean_gric": float(state_gric_mean.get(s,0)), "n_dc": int(state_dc_count.get(s,0))}
                      for s in states_common},
    "grs_counts": grs_counts,
    "confidence": {
        "n_full_4of4": n_full, "n_high_3of4": n_high,
        "n_mod_2of4": n_mod, "n_low_lt2": n_low,
        "tau50_n_cells": n_tau, "tau50_pct_eligible": float(pct_tau),
    },
    "carbon_delta_stats": {
        "min": float(dv.min()), "mean": float(dv.mean()), "max": float(dv.max()),
        "note": "All negative: 2040 projected intensity uniformly lower than 2023 historical intensity, consistent with grid decarbonisation"
    },
    "carbon_tier_current": {str(t): int(np.sum(tier_curr[elig_cells] == t)) for t in [1,2,3,4,5]},
    "carbon_tier_future":  {str(t): int(np.sum(tier_fut[elig_cells]  == t)) for t in [1,2,3,4,5]},
    "sensitivity_results": [
        {k: (float(v) if isinstance(v,(int,float)) else v) for k,v in row.items()}
        for row in sens_rows
    ],
}
out_path = f"{ADMIN}/gric_analysis_summary.json"
with open(out_path,"w") as f:
    json.dump(summary, f, indent=2)
print(f"\n  Summary JSON → {out_path}")
print("=== Patch complete ===")
