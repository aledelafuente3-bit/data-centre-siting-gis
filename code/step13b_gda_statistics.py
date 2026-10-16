#!/usr/bin/env python3
"""
step13b_gda_statistics.py
Statistical validation of the GDA (Grid Demand & Availability) layers.

Run with gis_venv Python (scipy available):
  13_scripts/gis_venv/bin/python3 13_scripts/step13b_gda_statistics.py

Tests:
  1. Mann-Whitney U  — GDA at DC validation points vs. all eligible cells
  2. Spearman ρ      — GRIC S1 vs. GDA reserve margin (cell-level sample)
  3. Jaccard J       — top-25% GRIC cells vs. top-25% GDA cells
  4. State Spearman  — mean GDA score per state vs. observed DC count
  5. Percentile report — where do DC locations fall in the GDA score distribution?
"""

import os, json, subprocess
import numpy as np
from scipy import stats

BASE      = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
GDAL_BIN  = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
PROJ_ENV  = {**os.environ,
             "PROJ_LIB":  "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj",
             "GDAL_DATA": "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"}

RASTER_DIR = f"{BASE}/11_processed_layers/rasters"
VAL_GPKG   = f"{BASE}/06_VALIDATION/observed_data_center_points/data_centers_7state_EPSG5070.gpkg"
EXCL_CSV   = f"{BASE}/06_VALIDATION/extracted_scores/gric_s1_dc_scores.csv"

XMIN, YMIN, XMAX, YMAX = -2295000, 310000, 1791000, 2907000
RES   = 1000
NCOLS, NROWS = 4086, 2597
ND    = -9999.0

# State bounding boxes (EPSG:5070, generous buffers) — same as step12b
STATE_BOUNDS = {
    "AZ": (-1_750_000, 640_000,  -1_150_000, 1_120_000),
    "IL": (  320_000, 1_490_000,   880_000, 2_060_000),
    "IA": ( -280_000, 1_640_000,   650_000, 2_100_000),
    "OR": (-2_295_000, 1_680_000, -1_480_000, 2_250_000),
    "TX": (-1_250_000,  390_000,   360_000, 1_280_000),
    "VA": (1_230_000, 1_180_000, 1_791_000, 1_540_000),
    "WV": (  970_000, 1_200_000, 1_380_000, 1_530_000),
}
DC_COUNTS = {"AZ": 171, "IL": 246, "IA": 0, "OR": 93, "TX": 450, "VA": 615, "WV": 0}


def read_raster(tif):
    tmp = tif + ".stat.raw"
    r = subprocess.run(
        [f"{GDAL_BIN}/gdal_translate", "-of", "ENVI", "-ot", "Float32",
         "-co", "INTERLEAVE=BSQ", tif, tmp],
        env=PROJ_ENV, capture_output=True, text=True
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    arr = np.fromfile(tmp, dtype=np.float32).reshape(NROWS, NCOLS)
    for f in [tmp, tmp + ".hdr"]:
        try: os.remove(f)
        except: pass
    return arr


def xy_to_rc(x, y):
    """World coord → (row, col). Returns (-1,-1) if outside grid."""
    col = int((x - XMIN) / RES)
    row = int((YMAX - y) / RES)
    if 0 <= row < NROWS and 0 <= col < NCOLS:
        return row, col
    return -1, -1


def extract_points_from_gpkg(gpkg, raster_arr):
    """Extract raster values at all point features using ogr2ogr → CSV."""
    import tempfile, csv, os
    tmp_csv = gpkg + ".tmp_pts.csv"
    subprocess.run(
        [f"{GDAL_BIN}/ogr2ogr", "-f", "CSV", tmp_csv, gpkg,
         "-lco", "GEOMETRY=AS_XY"],
        env=PROJ_ENV, capture_output=True
    )
    vals = []
    try:
        with open(tmp_csv, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    x = float(row.get("X") or row.get("x") or row.get("geometry_x") or 0)
                    y = float(row.get("Y") or row.get("y") or row.get("geometry_y") or 0)
                    r, c = xy_to_rc(x, y)
                    if r >= 0:
                        v = raster_arr[r, c]
                        if v != ND and not np.isnan(v):
                            vals.append(float(v))
                except Exception:
                    pass
    finally:
        try: os.remove(tmp_csv)
        except: pass
    return np.array(vals)


# ─── Load rasters ────────────────────────────────────────────────────────────
print("Loading rasters...")
mask_arr = read_raster(f"{RASTER_DIR}/mask_7states_1km_EPSG5070.tif")
mask7    = (mask_arr == 1)

gric_arr = read_raster(f"{RASTER_DIR}/gric_s1_baseline_1km.tif")
gda_rm   = read_raster(f"{RASTER_DIR}/gda_reserve_margin_suit_1km.tif")
gda_ut   = read_raster(f"{RASTER_DIR}/gda_utilization_suit_1km.tif")

# Eligible cells (pass M0 and have GDA data)
eligible = mask7 & (gric_arr != ND) & ~np.isnan(gric_arr)
gda_valid = eligible & (gda_rm != ND) & ~np.isnan(gda_rm)
print(f"  Eligible GRIC cells  : {eligible.sum():,}")
print(f"  Cells with GDA data  : {gda_valid.sum():,}")

gric_flat  = gric_arr[gda_valid]
rm_flat    = gda_rm[gda_valid]
ut_flat    = gda_ut[gda_valid]

# ─── Extract GDA scores at DC validation points ───────────────────────────────
print("\nExtracting GDA scores at DC validation points...")
dc_rm = extract_points_from_gpkg(VAL_GPKG, gda_rm)
dc_ut = extract_points_from_gpkg(VAL_GPKG, gda_ut)
print(f"  DC points with GDA data: {len(dc_rm):,}")

results = {}

# ─── Test 1: Mann-Whitney U ──────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 1 — Mann-Whitney U: GDA at DC locations vs. eligible cells")
print("="*60)
print("H₀: DC locations draw from the same GDA distribution as all eligible cells")
print("H₁: DC locations have systematically lower GDA scores (market ignores headroom)")

# Sample background to keep computation fast (n=10,000)
rng = np.random.default_rng(42)
bg_sample = rng.choice(rm_flat, size=min(10_000, len(rm_flat)), replace=False)

stat_rm, p_rm = stats.mannwhitneyu(dc_rm, bg_sample, alternative="less")
stat_ut, p_ut = stats.mannwhitneyu(dc_ut, bg_sample[:len(dc_rm)], alternative="less")

r_rm = 1 - (2 * stat_rm) / (len(dc_rm) * len(bg_sample))  # rank-biserial effect size

print(f"\n  Reserve margin suitability:")
print(f"    DC mean ± SD     : {dc_rm.mean():.3f} ± {dc_rm.std():.3f}")
print(f"    Background mean  : {rm_flat.mean():.3f} ± {rm_flat.std():.3f}")
print(f"    U statistic      : {stat_rm:,.0f}")
print(f"    p-value (one-sided, DC < background): {p_rm:.4f}")
print(f"    Rank-biserial r  : {r_rm:.3f}")
sig = "✓ significant" if p_rm < 0.05 else "✗ not significant"
print(f"    Result           : {sig}")

results["test1_mannwhitney"] = {
    "dc_mean_rm": round(float(dc_rm.mean()), 3),
    "background_mean_rm": round(float(rm_flat.mean()), 3),
    "U": float(stat_rm), "p_onesided": float(p_rm),
    "rank_biserial_r": round(float(r_rm), 3),
    "significant_p05": bool(p_rm < 0.05)
}

# ─── Test 2: Spearman ρ — GRIC vs. GDA (cell-level sample) ──────────────────
print("\n" + "="*60)
print("TEST 2 — Spearman ρ: GRIC S1 vs. GDA reserve margin")
print("="*60)
print("H₀: No monotonic association between GRIC scores and GDA headroom")
print("Purpose: if ρ is low, GDA adds independent spatial information to GRIC")

# Sample 50,000 cells for tractable computation
n_sample = min(50_000, len(gric_flat))
idx = rng.choice(len(gric_flat), size=n_sample, replace=False)
g_samp = gric_flat[idx]
r_samp = rm_flat[idx]

rho, p_rho = stats.spearmanr(g_samp, r_samp)
print(f"\n  Sample size : {n_sample:,} cells")
print(f"  Spearman ρ  : {rho:.3f}")
print(f"  p-value     : {p_rho:.2e}")
if abs(rho) < 0.20:
    interp = "weak — GDA adds largely independent spatial information to GRIC"
elif abs(rho) < 0.40:
    interp = "moderate — partial overlap; GDA adds meaningful independent signal"
else:
    interp = "strong — GDA and GRIC largely agree spatially"
print(f"  Interpretation: {interp}")

results["test2_spearman_gric_gda"] = {
    "n_sample": n_sample, "rho": round(float(rho), 3),
    "p_value": float(p_rho), "interpretation": interp
}

# ─── Test 3: Jaccard — top-25% GRIC vs. top-25% GDA ─────────────────────────
print("\n" + "="*60)
print("TEST 3 — Jaccard overlap: top-25% GRIC cells vs. top-25% GDA cells")
print("="*60)
print("Purpose: what fraction of the best-scoring GRIC zones also have high grid headroom?")

q75_gric = np.percentile(gric_flat, 75)
q75_gda  = np.percentile(rm_flat,  75)

top_gric = gric_flat >= q75_gric
top_gda  = rm_flat  >= q75_gda

intersection = np.sum(top_gric & top_gda)
union        = np.sum(top_gric | top_gda)
jaccard      = float(intersection) / float(union)

# Also compute: of top GRIC cells, what % are also top GDA?
pct_gric_also_top_gda = intersection / np.sum(top_gric) * 100

print(f"\n  GRIC p75 threshold : {q75_gric:.3f}")
print(f"  GDA RM p75 threshold: {q75_gda:.3f}")
print(f"  Top-25% GRIC cells  : {np.sum(top_gric):,}")
print(f"  Top-25% GDA cells   : {np.sum(top_gda):,}")
print(f"  Intersection        : {intersection:,}")
print(f"  Union               : {union:,}")
print(f"  Jaccard J           : {jaccard:.3f}")
print(f"  Of top GRIC cells, {pct_gric_also_top_gda:.1f}% also rank top-25% on GDA")

results["test3_jaccard"] = {
    "gric_p75": round(float(q75_gric), 3),
    "gda_rm_p75": round(float(q75_gda), 3),
    "n_top_gric": int(np.sum(top_gric)),
    "n_top_gda": int(np.sum(top_gda)),
    "intersection": int(intersection),
    "jaccard": round(jaccard, 3),
    "pct_top_gric_also_top_gda": round(float(pct_gric_also_top_gda), 1)
}

# ─── Test 4: State-level Spearman ρ ──────────────────────────────────────────
print("\n" + "="*60)
print("TEST 4 — State Spearman ρ: mean GDA score per state vs. DC count")
print("="*60)
print("Purpose: mirrors GRIC state-level validation; does GDA score predict market siting?")
print("(Expect INVERSE — market sites where GDA is LOW, i.e. market ignores grid stress)")

state_gda_means = {}
for state, (x0, y0, x1, y1) in STATE_BOUNDS.items():
    c0 = max(0, int((x0 - XMIN) / RES))
    c1 = min(NCOLS, int((x1 - XMIN) / RES))
    r0 = max(0, int((YMAX - y1) / RES))
    r1 = min(NROWS, int((YMAX - y0) / RES))
    patch_rm   = gda_rm[r0:r1, c0:c1]
    patch_mask = mask7[r0:r1, c0:c1]
    patch_gda_valid = gda_valid[r0:r1, c0:c1]
    valid_rm = patch_rm[patch_gda_valid]
    if len(valid_rm) > 0:
        state_gda_means[state] = float(valid_rm.mean())
    else:
        state_gda_means[state] = None

print(f"\n  {'State':5s} {'Mean GDA RM':>12} {'DC count':>10}")
print(f"  {'-'*32}")
for s in ["OR", "IA", "WV", "VA", "IL", "TX", "AZ"]:
    mean = state_gda_means.get(s)
    dc   = DC_COUNTS.get(s, 0)
    mean_str = f"{mean:>12.3f}" if mean is not None else "         N/A"
    print(f"  {s:5s} {mean_str} {dc:>10}")

# State-level Spearman (only states with DCs, like GRIC validation)
states_with_dc = [(s, state_gda_means[s], DC_COUNTS[s])
                  for s in STATE_BOUNDS
                  if state_gda_means.get(s) is not None
                  and not np.isnan(state_gda_means[s])
                  and DC_COUNTS.get(s, 0) > 0]
gda_vals  = [x[1] for x in states_with_dc]
dc_vals   = [x[2] for x in states_with_dc]
st_labels = [x[0] for x in states_with_dc]

rho_s, p_s = stats.spearmanr(gda_vals, dc_vals)
print(f"\n  States included: {st_labels}")
print(f"  n states (with DCs): {len(states_with_dc)}")
print(f"  Spearman ρ: {rho_s:.3f}")
print(f"  p-value   : {p_s:.3f}")
if rho_s < -0.3:
    interp_s = "negative — market sites where GDA scores are lower (market ignores grid stress)"
elif rho_s < 0.3:
    interp_s = "near-zero — no clear relationship between GDA headroom and market siting"
else:
    interp_s = "positive — market sites where GDA scores are higher"
print(f"  Interpretation: {interp_s}")

results["test4_state_spearman"] = {
    "states_included": st_labels,
    "n": len(states_with_dc),
    "rho": round(float(rho_s), 3),
    "p_value": round(float(p_s), 3),
    "interpretation": interp_s
}

# ─── Test 5: DC percentile rank in GDA distribution ──────────────────────────
print("\n" + "="*60)
print("TEST 5 — DC percentile rank in GDA distribution")
print("="*60)
print("What fraction of eligible cells score LOWER on GDA than the average DC location?")

pct_rank_rm = float(np.mean(rm_flat < dc_rm.mean()) * 100)
pct_rank_ut = float(np.mean(ut_flat < dc_ut.mean()) * 100)

print(f"\n  Mean GDA RM at DC locations   : {dc_rm.mean():.3f}")
print(f"  Percentile rank in distribution: {pct_rank_rm:.1f}th percentile")
print(f"  → {pct_rank_rm:.1f}% of eligible cells have LOWER grid headroom than the avg DC")
print(f"\n  Mean GDA Util at DC locations  : {dc_ut.mean():.3f}")
print(f"  Percentile rank in distribution: {pct_rank_ut:.1f}th percentile")

capture_top10 = float(np.mean(dc_rm >= np.percentile(rm_flat, 90)) * 100)
capture_top25 = float(np.mean(dc_rm >= np.percentile(rm_flat, 75)) * 100)
print(f"\n  DC capture in top-10% GDA zone : {capture_top10:.1f}%  (random = 10%)")
print(f"  DC capture in top-25% GDA zone : {capture_top25:.1f}%  (random = 25%)")
if capture_top10 < 10:
    print(f"  → DCs are UNDER-represented in high-headroom zones ({capture_top10:.1f}% vs 10% random)")
elif capture_top10 > 10:
    print(f"  → DCs are OVER-represented in high-headroom zones ({capture_top10:.1f}% vs 10% random)")

results["test5_dc_percentile"] = {
    "dc_mean_rm": round(float(dc_rm.mean()), 3),
    "dc_percentile_rank_in_rm_dist": round(pct_rank_rm, 1),
    "capture_top10pct_gda": round(capture_top10, 1),
    "capture_top25pct_gda": round(capture_top25, 1),
    "random_expectation_top10": 10.0,
    "random_expectation_top25": 25.0
}

# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"  T1 Mann-Whitney: DC locations have lower GDA RM (p={p_rm:.4f}, r={r_rm:.3f})")
print(f"  T2 Spearman ρ (GRIC × GDA): ρ={rho:.3f} — {interp}")
print(f"  T3 Jaccard J (top-25% overlap): J={jaccard:.3f}, {pct_gric_also_top_gda:.1f}% of top-GRIC cells also top-GDA")
print(f"  T4 State Spearman (GDA × DC count): ρ={rho_s:.3f} — {interp_s}")
print(f"  T5 DC capture in top-10% GDA: {capture_top10:.1f}% (random=10%)")

out_path = f"{BASE}/00_ADMIN/gda_statistics.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved → {out_path}")
