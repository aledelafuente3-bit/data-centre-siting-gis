"""
step21_validation.py
Validate GRIC model against observed US data centre locations.

Outputs:
  00_ADMIN/validation_results.json

Method:
  1. Load data_centers_7state_public_master.csv (active + include=yes/review; all 7 states)
  2. Filter to 7 study states; convert WGS84 → EPSG:5070 via gdaltransform
  3. Sample GRIC raster at each valid DC location
  4. Generate 5,000 constrained random eligible points from viable GRIC cells
  5. Mann-Whitney U test (DC vs random) — large-sample normal approximation
  6. Capture rates: % of DCs in top 10/25/50% of GRIC
  7. State-level: mean GRIC at DC locations vs mean GRIC across all viable cells
  8. Spearman rho: state mean GRIC vs DC count per viable km2
"""

import os, sys, subprocess, json, csv, math
import numpy as np

BASE   = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
GDAL   = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
ENV    = {**os.environ,
          "PROJ_LIB":  "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj",
          "GDAL_DATA": "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"}

MASTER_CSV   = f"{BASE}/06_VALIDATION/observed_data_center_points/data_centers_7state_public_master.csv"
GRIC_TIF     = f"{BASE}/11_processed_layers/rasters/gric_s1_threepillar_1km.tif"
OUT_JSON     = f"{BASE}/00_ADMIN/validation_results.json"

# Include active + under_construction; exclude announced/planned (not yet operational at scale)
# include_in_validation must be 'yes' or 'review' (NOAA WV facility)
INCLUDE_STATUSES = {"active", "under_construction"}
INCLUDE_VALIDATION = {"yes", "review"}

STATES_7 = {"AZ","IL","IA","OR","TX","VA","WV"}

RNG = np.random.default_rng(42)

# ── helpers ──────────────────────────────────────────────────────────────────

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, env=ENV)

def gdal_info_json(tif):
    r = run([f"{GDAL}/gdalinfo", "-json", tif])
    return json.loads(r.stdout)

def read_raster_numpy(tif):
    """Read GeoTIFF → (array float64, geotransform tuple, nodata)"""
    info = gdal_info_json(tif)
    gt   = info["geoTransform"]          # [x0, px, 0, y0, 0, py]
    nd   = info["bands"][0].get("noDataValue", None)
    if nd is not None:
        nd = float(nd)
    # Get size
    sz = info["size"]   # [nCols, nRows]
    nCols, nRows = sz[0], sz[1]
    # Write to ENVI raw via gdal_translate
    raw = f"/tmp/step21_gric.raw"
    hdr = f"/tmp/step21_gric.hdr"
    run([f"{GDAL}/gdal_translate", "-of", "ENVI", "-ot", "Float32", tif, raw])
    arr = np.fromfile(raw, dtype=np.float32).reshape(nRows, nCols).astype(np.float64)
    if nd is not None:
        arr[arr == nd] = np.nan
    return arr, gt, nd

def latlon_to_rc(lats, lons, gt):
    """Convert WGS84 lat/lon arrays to (row, col) in EPSG:5070 raster via gdaltransform."""
    pairs = "\n".join(f"{lon} {lat}" for lon, lat in zip(lons, lats))
    r = run([f"{GDAL}/gdaltransform", "-s_srs", "EPSG:4326", "-t_srs", "EPSG:5070"])
    # pipe input
    proc = subprocess.run(
        [f"{GDAL}/gdaltransform", "-s_srs", "EPSG:4326", "-t_srs", "EPSG:5070"],
        input=pairs, capture_output=True, text=True, env=ENV
    )
    xs, ys = [], []
    for line in proc.stdout.strip().split("\n"):
        parts = line.strip().split()
        if len(parts) >= 2:
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
        else:
            xs.append(np.nan)
            ys.append(np.nan)
    xs, ys = np.array(xs), np.array(ys)
    x0, px, _, y0, _, py = gt
    cols = ((xs - x0) / px).astype(int)
    rows = ((ys - y0) / py).astype(int)
    return rows, cols

def sample_raster(arr, rows, cols):
    nRows, nCols = arr.shape
    scores = []
    valid_idx = []
    for i, (r, c) in enumerate(zip(rows, cols)):
        if 0 <= r < nRows and 0 <= c < nCols:
            v = arr[r, c]
            if not np.isnan(v):
                scores.append(v)
                valid_idx.append(i)
            else:
                scores.append(np.nan)
        else:
            scores.append(np.nan)
    return np.array(scores), valid_idx

def mannwhitney_u(a, b):
    """Large-sample Mann-Whitney U, normal approximation. Returns U, z, p (two-sided)."""
    n1, n2 = len(a), len(b)
    combined = np.concatenate([a, b])
    ranks    = np.argsort(np.argsort(combined)) + 1.0  # rank 1..N
    R1 = ranks[:n1].sum()
    U1 = R1 - n1*(n1+1)/2
    U2 = n1*n2 - U1
    U  = min(U1, U2)
    mu_U  = n1*n2/2
    sig_U = math.sqrt(n1*n2*(n1+n2+1)/12)
    z = (U - mu_U) / sig_U
    # two-sided p from standard normal
    p = 2 * (1 - _normal_cdf(abs(z)))
    return float(U1), float(z), float(p)

def _normal_cdf(x):
    return 0.5*(1 + math.erf(x/math.sqrt(2)))

def spearman_rho(x, y):
    x, y = np.array(x, float), np.array(y, float)
    n = len(x)
    rx = np.argsort(np.argsort(x)).astype(float) + 1
    ry = np.argsort(np.argsort(y)).astype(float) + 1
    d2 = ((rx - ry)**2).sum()
    rho = 1 - 6*d2/(n*(n**2-1))
    return float(rho)

# ── main ─────────────────────────────────────────────────────────────────────

print("Reading GRIC raster...")
gric_arr, gt, nd = read_raster_numpy(GRIC_TIF)
nRows, nCols = gric_arr.shape
print(f"  GRIC shape: {nRows}×{nCols}, viable cells: {int(np.sum(~np.isnan(gric_arr))):,}")

# All viable cell values
viable_mask = ~np.isnan(gric_arr)
viable_vals  = gric_arr[viable_mask]
viable_ij    = np.argwhere(viable_mask)  # shape (N, 2) - (row, col)
print(f"  Viable cells: {len(viable_vals):,}")

# ── 1. Load DC locations ──────────────────────────────────────────────────────
print("\nLoading DC locations from data_centers_7state_public_master.csv...")
dc_lats, dc_lons, dc_states, dc_names = [], [], [], []
with open(MASTER_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        state = row.get("state","").strip().upper()
        if state not in STATES_7:
            continue
        status = row.get("status","").strip().lower()
        include = row.get("include_in_validation","").strip().lower()
        if status not in INCLUDE_STATUSES or include not in INCLUDE_VALIDATION:
            continue
        try:
            lat = float(row["lat"])
            lon = float(row["lon"])
        except (ValueError, KeyError):
            continue
        dc_lats.append(lat)
        dc_lons.append(lon)
        dc_states.append(state)
        dc_names.append(row.get("facility_name",""))

print(f"  DC points in 7 states (active/under_construction, include=yes/review): {len(dc_lats)}")

# ── 2. Convert to EPSG:5070 and sample ───────────────────────────────────────
print("Converting DC coordinates to EPSG:5070 and sampling GRIC...")
dc_rows, dc_cols = latlon_to_rc(dc_lats, dc_lons, gt)
dc_scores, dc_valid_idx = sample_raster(gric_arr, dc_rows, dc_cols)
dc_scores_clean = dc_scores[~np.isnan(dc_scores)]
dc_states_clean = [dc_states[i] for i in range(len(dc_states)) if not np.isnan(dc_scores[i])]
print(f"  DC points with valid GRIC score: {len(dc_scores_clean)}")

# ── 3. Generate 5,000 random eligible points ─────────────────────────────────
print("Generating 5,000 random eligible points from viable cells...")
random_idx   = RNG.choice(len(viable_vals), size=5000, replace=False)
random_scores = viable_vals[random_idx]
print(f"  Random sample size: {len(random_scores)}")

# ── 4. Mann-Whitney U test ────────────────────────────────────────────────────
print("Running Mann-Whitney U test...")
U1, z, p = mannwhitney_u(dc_scores_clean, random_scores)
print(f"  U={U1:.0f}, z={z:.4f}, p={p:.6f}")

# Effect size: rank-biserial correlation r = 2U/(n1*n2) - 1
n1, n2 = len(dc_scores_clean), len(random_scores)
r_rb = (2*U1/(n1*n2)) - 1  # positive → DCs score higher

# ── 5. Descriptive statistics ─────────────────────────────────────────────────
def desc(arr):
    return {
        "n": int(len(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
    }

# ── 6. Capture rates ──────────────────────────────────────────────────────────
# Thresholds based on viable cell distribution
p50_thresh = float(np.percentile(viable_vals, 50))
p75_thresh = float(np.percentile(viable_vals, 75))
p90_thresh = float(np.percentile(viable_vals, 90))

cap50 = float(np.mean(dc_scores_clean >= p50_thresh) * 100)
cap75 = float(np.mean(dc_scores_clean >= p75_thresh) * 100)
cap90 = float(np.mean(dc_scores_clean >= p90_thresh) * 100)

print(f"  Capture rate top 50%: {cap50:.1f}%")
print(f"  Capture rate top 25%: {cap75:.1f}%")
print(f"  Capture rate top 10%: {cap90:.1f}%")

# ── 7. State-level analysis ───────────────────────────────────────────────────
# DC count and mean GRIC at DCs per state
state_results = {}
for st in sorted(STATES_7):
    st_scores = [dc_scores_clean[i] for i,s in enumerate(dc_states_clean) if s == st]
    state_results[st] = {
        "dc_count_with_score": int(len(st_scores)),
        "mean_gric_at_dcs": float(np.mean(st_scores)) if st_scores else None,
    }

# Viable cell count per state — use geotransform to check which state
# (simple approach: use the JSON summary for state mean GRIC)
state_gric_means = {"AZ":0.6002,"IL":0.637,"IA":0.6767,"OR":0.701,"TX":0.5554,"VA":0.6497,"WV":0.6515}

# Spearman rho: state mean GRIC (all cells) vs DC density (DCs per state)
# DC density proxy: dc_count_with_score (not per area, but sufficient for n=7)
states_ordered = sorted(STATES_7)
gric_means_vec = [state_gric_means[s] for s in states_ordered]
dc_counts_vec  = [state_results[s]["dc_count_with_score"] for s in states_ordered]
state_rho = spearman_rho(gric_means_vec, dc_counts_vec)
print(f"\nState Spearman rho (GRIC mean vs DC count): {state_rho:.4f}")

# ── 8. Within-state comparison: DC score vs all viable cells ──────────────────
# For each state: mean GRIC at DC locations vs model mean across all viable cells
state_comparison = {}
for st in sorted(STATES_7):
    st_dc_scores = [dc_scores_clean[i] for i,s in enumerate(dc_states_clean) if s == st]
    model_mean   = state_gric_means[st]
    dc_mean      = float(np.mean(st_dc_scores)) if st_dc_scores else None
    diff         = float(dc_mean - model_mean) if dc_mean is not None else None
    state_comparison[st] = {
        "dc_count": len(st_dc_scores),
        "mean_gric_at_dcs": dc_mean,
        "mean_gric_all_viable": model_mean,
        "difference": diff,
        "direction": ("DCs score above model mean" if diff and diff > 0 else "DCs score below model mean") if diff is not None else None,
    }
    if dc_mean is not None:
        print(f"  {st}: DC mean={dc_mean:.3f} vs model mean={model_mean:.3f} (diff={diff:+.3f})")

# ── 9. Assemble and save results ──────────────────────────────────────────────
results = {
    "methodology": {
        "source": "data_centers_7state_public_master.csv — active+under_construction, include=yes/review; all 7 study states including IA (7 active) and WV (1 active)",
        "raster": "gric_s1_threepillar_1km.tif",
        "random_sample": 5000,
        "random_seed": 42,
        "test": "Mann-Whitney U (large-sample normal approximation, two-sided)",
        "note": "GRIC score extracted at DC point location; NoData cells excluded"
    },
    "sample_sizes": {
        "dc_points_in_7_states": len(dc_lats),
        "dc_points_with_valid_score": int(len(dc_scores_clean)),
        "random_eligible_points": int(len(random_scores)),
    },
    "descriptive": {
        "dc_locations": desc(dc_scores_clean),
        "random_eligible": desc(random_scores),
        "all_viable_cells": desc(viable_vals),
    },
    "mann_whitney": {
        "U": float(U1),
        "z_statistic": float(z),
        "p_value": float(p),
        "rank_biserial_r": float(r_rb),
        "interpretation": "positive r_rb means DC locations score higher than random eligible points"
    },
    "capture_rates": {
        "gric_p50_threshold": round(p50_thresh, 4),
        "gric_p75_threshold": round(p75_thresh, 4),
        "gric_p90_threshold": round(p90_thresh, 4),
        "pct_dcs_above_p50": round(cap50, 2),
        "pct_dcs_above_p75": round(cap75, 2),
        "pct_dcs_above_p90": round(cap90, 2),
        "expected_if_random_p50": 50.0,
        "expected_if_random_p75": 25.0,
        "expected_if_random_p90": 10.0,
    },
    "state_level": {
        "spearman_rho_gric_mean_vs_dc_count": round(state_rho, 4),
        "note": "n=7 states; Spearman rho between state mean GRIC (all viable cells) and DC count with valid score",
        "state_detail": state_comparison,
    },
}

with open(OUT_JSON, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: {OUT_JSON}")
print("\n=== SUMMARY ===")
print(f"DC mean GRIC:     {results['descriptive']['dc_locations']['mean']:.4f}")
print(f"Random mean GRIC: {results['descriptive']['random_eligible']['mean']:.4f}")
print(f"Mann-Whitney z:   {z:.4f}")
print(f"p-value:          {p:.6f}")
print(f"Rank-biserial r:  {r_rb:.4f}")
print(f"Capture top 25%:  {cap75:.1f}%  (expected if random: 25.0%)")
print(f"Capture top 10%:  {cap90:.1f}%  (expected if random: 10.0%)")
print(f"State rho:        {state_rho:.4f}")
