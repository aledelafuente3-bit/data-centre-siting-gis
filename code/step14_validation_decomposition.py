#!/usr/bin/env python3
"""
step14_validation_decomposition.py
Task 1: Validation decomposition table — OFI vs ESI vs GRIC lift analysis.

Run with gis_venv Python (scipy available):
  /Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/13_scripts/gis_venv/bin/python3 \
      step14_validation_decomposition.py

Outputs:
  00_ADMIN/validation_decomposition.json
  (printed table for copy-paste into dissertation)
"""

import os, sys, json, subprocess, csv
import numpy as np
from scipy import stats

BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RDIR     = f"{BASE}/11_processed_layers/rasters"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
PROJ_ENV = {**os.environ,
            "PROJ_LIB":  "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj",
            "GDAL_DATA": "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"}

NROWS, NCOLS = 2597, 4086
XMIN, YMIN   = -2295000, 310000
RES          = 1000
ND           = -9999.0

DC_GPKG = f"{BASE}/06_VALIDATION/observed_data_center_points/data_centers_7state_EPSG5070.gpkg"


# ── helpers ──────────────────────────────────────────────────────────────────

def run(cmd):
    r = subprocess.run(cmd, env=PROJ_ENV, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr}")
    return r.stdout

def read_raster(tif):
    tmp = tif + ".tmp14.raw"
    run([f"{GDAL_BIN}/gdal_translate", "-of", "ENVI", "-ot", "Float32",
         "-co", "INTERLEAVE=BSQ", tif, tmp])
    arr = np.fromfile(tmp, dtype=np.float32).reshape(NROWS, NCOLS)
    for f in [tmp, tmp + ".hdr"]:
        try: os.remove(f)
        except: pass
    arr = arr.astype(np.float64)
    arr[arr == ND] = np.nan
    arr[arr == -9999.0] = np.nan
    return arr

def rc_to_xy(row, col):
    """Convert raster row/col to EPSG:5070 X,Y (cell centre)."""
    x = XMIN + col * RES + RES / 2
    y = YMIN + (NROWS - 1 - row) * RES + RES / 2
    return x, y

def xy_to_rc(x, y):
    """Convert EPSG:5070 X,Y to raster row/col."""
    col = int((x - XMIN) / RES)
    row = int(NROWS - 1 - (y - YMIN) / RES)
    return row, col


# ── Stage 0: Load rasters ────────────────────────────────────────────────────

print("\n=== Stage 0: Loading rasters ===")

mask    = read_raster(f"{RDIR}/mask_7states_1km_EPSG5070.tif")
pad12   = read_raster(f"{RDIR}/pad_us_gap12_exclusion_1km.tif")
water_wl= read_raster(f"{RDIR}/pct_waterwetland_1km_EPSG5070.tif")
eligible= read_raster(f"{RDIR}/pct_eligible_1km_EPSG5070.tif")
floodway= read_raster(f"{RDIR}/nfhl_floodway_fraction_1km.tif")
sfha    = read_raster(f"{RDIR}/nfhl_sfha_fraction_1km.tif")

water_s = read_raster(f"{RDIR}/water_stress_baseline_bws_suitability.tif")
wildfire= read_raster(f"{RDIR}/nri_wildfire_suitability_1km.tif")
flood   = read_raster(f"{RDIR}/nri_inland_flood_suitability_1km.tif")
tx230   = read_raster(f"{RDIR}/hifld_tx_230kV_proximity_1km.tif")
road    = read_raster(f"{RDIR}/tiger_roads_prisec_proximity_1km.tif")
gric    = read_raster(f"{RDIR}/gric_s1_baseline_1km.tif")

print("  All rasters loaded.")


# ── Stage 1: Rebuild exclusion mask + ESI + OFI ──────────────────────────────

print("\n=== Stage 1: Rebuild exclusion mask + ESI + OFI ===")

mask7 = ~np.isnan(mask)

excl = np.zeros((NROWS, NCOLS), dtype=bool)
excl |= (pad12 == 1)
wl = np.nan_to_num(water_wl, nan=0.0); excl |= (wl >= 0.50)
el = np.nan_to_num(eligible,  nan=0.0); excl |= (el < 0.10)
fw = np.nan_to_num(floodway,  nan=0.0); excl |= (fw > 0)
sf = np.nan_to_num(sfha,      nan=0.0); excl |= (sf >= 0.25)
excl |= ~mask7

eligible_mask = mask7 & ~excl
n_elig = eligible_mask.sum()
print(f"  Eligible cells: {n_elig:,}")

# Reconstruct ESI (Mode A: water=3/7, wildfire=2/7, flood=2/7)
all_esi_valid = (~np.isnan(water_s)) & (~np.isnan(wildfire)) & (~np.isnan(flood))
esi = (3/7) * np.nan_to_num(water_s, nan=0) + \
      (2/7) * np.nan_to_num(wildfire, nan=0) + \
      (2/7) * np.nan_to_num(flood,    nan=0)
esi[~all_esi_valid] = np.nan

# Reconstruct OFI (TX 70%, road 30%)
suit_tx   = np.clip(1.0 - tx230 / 100000.0, 0.0, 1.0)
suit_tx[np.isnan(tx230)] = np.nan
suit_road = np.clip(1.0 - road / 30000.0, 0.0, 1.0)
suit_road[np.isnan(road)] = np.nan
all_ofi_valid = (~np.isnan(suit_tx)) & (~np.isnan(suit_road))
ofi = 0.70 * np.nan_to_num(suit_tx,   nan=0) + \
      0.30 * np.nan_to_num(suit_road,  nan=0)
ofi[~all_ofi_valid] = np.nan

print(f"  ESI valid eligible cells: {np.sum(~np.isnan(esi) & eligible_mask):,}")
print(f"  OFI valid eligible cells: {np.sum(~np.isnan(ofi) & eligible_mask):,}")
print(f"  GRIC valid eligible cells: {np.sum(~np.isnan(gric) & eligible_mask):,}")


# ── Stage 2: Extract DC point coordinates ────────────────────────────────────

print("\n=== Stage 2: Extract DC point coordinates ===")

tmp_csv = f"{BASE}/00_ADMIN/_dc_pts_tmp.csv"
run([f"{GDAL_BIN}/ogr2ogr", "-f", "CSV", tmp_csv, DC_GPKG,
     "-lco", "GEOMETRY=AS_XY"])

dc_points = []
with open(tmp_csv) as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            x = float(row["X"]); y = float(row["Y"])
            dc_points.append((x, y))
        except (ValueError, KeyError):
            pass
try: os.remove(tmp_csv)
except: pass

print(f"  DC points loaded: {len(dc_points):,}")


# ── Stage 3: Sample each surface at DC locations ─────────────────────────────

print("\n=== Stage 3: Sample surfaces at DC locations ===")

def sample_surface(arr, points, eligible_mask, name):
    vals = []
    n_excluded = 0
    n_oob = 0
    n_nan = 0

    for (x, y) in points:
        row, col = xy_to_rc(x, y)
        if row < 0 or row >= NROWS or col < 0 or col >= NCOLS:
            n_oob += 1
            continue
        if not eligible_mask[row, col]:
            n_excluded += 1
            continue
        v = arr[row, col]
        if np.isnan(v):
            n_nan += 1
            continue
        vals.append(v)

    print(f"  {name}: {len(vals)} scored | {n_excluded} in excluded cells "
          f"| {n_oob} out-of-bounds | {n_nan} NoData")
    return np.array(vals), n_excluded

dc_esi,  n_excl_esi  = sample_surface(esi,  dc_points, eligible_mask, "ESI")
dc_ofi,  n_excl_ofi  = sample_surface(ofi,  dc_points, eligible_mask, "OFI")
dc_gric, n_excl_gric = sample_surface(gric, dc_points, eligible_mask, "GRIC")


# ── Stage 4: Compute percentile ranks + lift ─────────────────────────────────

print("\n=== Stage 4: Percentile ranks and lift ===")

# Reference distributions (eligible cells only)
esi_ref  = esi[eligible_mask  & ~np.isnan(esi)]
ofi_ref  = ofi[eligible_mask  & ~np.isnan(ofi)]
gric_ref = gric[eligible_mask & ~np.isnan(gric)]

def percentile_rank(val, reference):
    """Fraction of reference cells scoring at or below val."""
    return float(np.mean(reference <= val))

def analyse(dc_vals, ref_dist, name):
    pct_ranks = np.array([percentile_rank(v, ref_dist) for v in dc_vals])
    median_pct = float(np.median(pct_ranks)) * 100
    top_decile_share = float(np.mean(pct_ranks >= 0.90)) * 100
    lift = top_decile_share / 10.0  # 10% expected at random

    print(f"\n  {name}:")
    print(f"    DCs scored:              {len(dc_vals):,}")
    print(f"    Median percentile rank:  {median_pct:.1f}th")
    print(f"    Share in top decile:     {top_decile_share:.1f}%")
    print(f"    Top-decile lift:         {lift:.2f}×")
    print(f"    (25th / 75th pct of DC ranks): "
          f"{np.percentile(pct_ranks,25)*100:.1f} / {np.percentile(pct_ranks,75)*100:.1f}")

    return {
        "n_scored": int(len(dc_vals)),
        "n_in_excluded_cells": int(n_excl_esi if name=="ESI" else n_excl_ofi if name=="OFI" else n_excl_gric),
        "median_percentile": round(median_pct, 1),
        "top_decile_share_pct": round(top_decile_share, 1),
        "lift": round(lift, 2),
        "p25_rank": round(float(np.percentile(pct_ranks, 25)) * 100, 1),
        "p75_rank": round(float(np.percentile(pct_ranks, 75)) * 100, 1),
    }

results = {}
results["ESI"]  = analyse(dc_esi,  esi_ref,  "ESI")
results["OFI"]  = analyse(dc_ofi,  ofi_ref,  "OFI")
results["GRIC"] = analyse(dc_gric, gric_ref, "GRIC")

# ── Stage 5: Print clean table ───────────────────────────────────────────────

print("\n\n" + "="*70)
print("  VALIDATION DECOMPOSITION TABLE")
print("="*70)
print(f"  {'Surface':<8} {'N scored':>10} {'In excl.':>10} {'Median pct':>12} "
      f"{'Top-10% share':>15} {'Lift':>8}")
print("-"*70)
for name in ["ESI", "OFI", "GRIC"]:
    r = results[name]
    print(f"  {name:<8} {r['n_scored']:>10,} {r['n_in_excluded_cells']:>10,} "
          f"{r['median_percentile']:>11.1f}th {r['top_decile_share_pct']:>14.1f}% "
          f"{r['lift']:>7.2f}×")
print("="*70)
print(f"\n  Key finding:")
print(f"  OFI lift = {results['OFI']['lift']:.2f}×  |  "
      f"ESI lift = {results['ESI']['lift']:.2f}×  |  "
      f"GRIC lift = {results['GRIC']['lift']:.2f}×")

ofi_l = results["OFI"]["lift"]
esi_l = results["ESI"]["lift"]
gap   = ofi_l - esi_l
if gap > 0.5:
    print(f"\n  ✓ Market-sustainability gap confirmed: OFI {gap:.2f}× higher than ESI.")
    print(f"    The industry optimises operational access and systematically")
    print(f"    underweights environmental suitability.")
elif gap < -0.5:
    print(f"\n  ESI lift > OFI lift — industry may be partially sustainability-driven.")
else:
    print(f"\n  OFI and ESI lifts are similar — both dimensions are co-optimised.")

# ── Stage 6: Mann-Whitney U per surface ─────────────────────────────────────

print("\n=== Stage 5: Mann-Whitney U (DC vs background) ===")

for name, dc_v, ref_v in [("ESI", dc_esi, esi_ref), ("OFI", dc_ofi, ofi_ref), ("GRIC", dc_gric, gric_ref)]:
    bg_sample = np.random.default_rng(42).choice(ref_v, size=min(50000, len(ref_v)), replace=False)
    stat, p = stats.mannwhitneyu(dc_v, bg_sample, alternative="greater")
    r_rb = 1 - (2 * stat) / (len(dc_v) * len(bg_sample))
    print(f"  {name}: U={stat:.0f}, p={p:.4e}, rank-biserial r={r_rb:.3f}")
    results[name]["mannwhitney_p"] = float(p)
    results[name]["mannwhitney_r"] = round(float(r_rb), 3)

# ── Save ─────────────────────────────────────────────────────────────────────

out = f"{BASE}/00_ADMIN/validation_decomposition.json"
with open(out, "w") as f:
    json.dump(results, f, indent=2)
print(f"\n→ {out}")
print("\n=== DONE ===")
