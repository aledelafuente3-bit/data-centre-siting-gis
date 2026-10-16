#!/usr/bin/env python3
"""
step15_scenarios_s2_s5.py
Task 2: Compute scenarios S2–S5 + robustness (Jaccard) analysis.
Task 3: Confidence layer stats + figure data.

Run with gis_venv Python:
  ./gis_venv/bin/python3 step15_scenarios_s2_s5.py
"""

import os, sys, json, subprocess
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
ND           = np.float32(-9999.0)


# ── helpers ──────────────────────────────────────────────────────────────────

def run(cmd):
    r = subprocess.run(cmd, env=PROJ_ENV, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr}")

def read_raster(tif):
    tmp = tif + ".tmp15.raw"
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
    """Write numpy float64 array as LZW GeoTIFF via ENVI raw + VRT → gdal_translate."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_raw = path + ".tmp15.raw"
    tmp_vrt = path + ".tmp15.vrt"
    out_tif = path

    a32 = arr.astype(np.float32)
    a32[np.isnan(arr)] = -9999.0
    a32.tofile(tmp_raw)

    # ENVI header so GDAL can read the raw binary
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

    if os.path.exists(out_tif): os.remove(out_tif)
    run([f"{GDAL_BIN}/gdal_translate",
         "-of", "GTiff", "-ot", "Float32",
         "-a_nodata", "-9999",
         "-co", "COMPRESS=LZW", "-co", "TILED=YES",
         tmp_vrt, out_tif])

    for f in [tmp_raw, tmp_raw + ".hdr", tmp_vrt]:
        try: os.remove(f)
        except: pass
    print(f"  → {os.path.basename(out_tif)}")


# ── Stage 0: Load all needed rasters ────────────────────────────────────────

print("\n=== Stage 0: Loading rasters ===")

mask    = read_raster(f"{RDIR}/mask_7states_1km_EPSG5070.tif")
pad12   = read_raster(f"{RDIR}/pad_us_gap12_exclusion_1km.tif")
water_wl= read_raster(f"{RDIR}/pct_waterwetland_1km_EPSG5070.tif")
eligible= read_raster(f"{RDIR}/pct_eligible_1km_EPSG5070.tif")
floodway= read_raster(f"{RDIR}/nfhl_floodway_fraction_1km.tif")
sfha    = read_raster(f"{RDIR}/nfhl_sfha_fraction_1km.tif")
eji_flag= read_raster(f"{RDIR}/eji_2024_flag_p75_1km.tif")
confidence = read_raster(f"{RDIR}/composite_confidence_1km.tif")

water_s = read_raster(f"{RDIR}/water_stress_baseline_bws_suitability.tif")
wildfire= read_raster(f"{RDIR}/nri_wildfire_suitability_1km.tif")
flood   = read_raster(f"{RDIR}/nri_inland_flood_suitability_1km.tif")
tx230   = read_raster(f"{RDIR}/hifld_tx_230kV_proximity_1km.tif")
road    = read_raster(f"{RDIR}/tiger_roads_prisec_proximity_1km.tif")
gric_s1 = read_raster(f"{RDIR}/gric_s1_baseline_1km.tif")

print("  All rasters loaded.")


# ── Stage 1: Exclusion mask ───────────────────────────────────────────────────

mask7 = (mask == 1) | ((mask > 0) & (mask < 255))  # value=1 means valid
# More robust: any non-NaN, non-255 cell
mask7 = ~np.isnan(mask) & (mask != 255.0)
# Fallback: use GRIC NaN pattern as the eligible mask
elig_from_gric = ~np.isnan(gric_s1)  # most reliable: wherever GRIC was computed

excl = np.zeros((NROWS, NCOLS), dtype=bool)
excl |= (np.nan_to_num(pad12,    nan=0.0) == 1)
excl |= (np.nan_to_num(water_wl, nan=0.0) >= 0.50)
excl |= (np.nan_to_num(eligible, nan=0.0) < 0.10)
excl |= (np.nan_to_num(floodway, nan=0.0) > 0)
excl |= (np.nan_to_num(sfha,     nan=0.0) >= 0.25)
excl |= ~elig_from_gric  # outside eligible area

eligible_mask = elig_from_gric & ~excl
# Use the GRIC surface's own eligible footprint directly
eligible_mask = elig_from_gric  # GRIC is already masked to eligible cells

n_elig = eligible_mask.sum()
print(f"  Eligible cells (from GRIC footprint): {n_elig:,}")


# ── Stage 2: Reconstruct ESI and OFI ─────────────────────────────────────────

print("\n=== Stage 2: Reconstruct ESI + OFI ===")

# OFI components (identical to step12)
suit_tx   = np.clip(1.0 - tx230 / 100000.0, 0.0, 1.0);  suit_tx[np.isnan(tx230)]  = np.nan
suit_road = np.clip(1.0 - road  / 30000.0,  0.0, 1.0);  suit_road[np.isnan(road)] = np.nan

all_esi_v = (~np.isnan(water_s)) & (~np.isnan(wildfire)) & (~np.isnan(flood))
all_ofi_v = (~np.isnan(suit_tx)) & (~np.isnan(suit_road))

def make_esi(w_water, w_wild, w_flood):
    e = (w_water * np.nan_to_num(water_s,  nan=0) +
         w_wild  * np.nan_to_num(wildfire, nan=0) +
         w_flood * np.nan_to_num(flood,    nan=0))
    e[~all_esi_v] = np.nan
    return e

def make_ofi():
    o = (0.70 * np.nan_to_num(suit_tx,   nan=0) +
         0.30 * np.nan_to_num(suit_road,  nan=0))
    o[~all_ofi_v] = np.nan
    return o

def make_gric_surface(esi, ofi, w_esi):
    all_v = (~np.isnan(esi)) & (~np.isnan(ofi))
    g = w_esi * np.nan_to_num(esi, nan=0) + (1-w_esi) * np.nan_to_num(ofi, nan=0)
    g[~all_v] = np.nan
    return g

def apply_eji_penalty(gric_arr, penalty=0.75):
    """Apply EJI penalty (same as V7 mechanism) in high-concern cells."""
    result = gric_arr.copy()
    flagged = (eji_flag == 1) & ~np.isnan(gric_arr)
    eji_s = np.nan_to_num(read_raster(f"{RDIR}/eji_2024_score_1km.tif"), nan=0)
    EJI_THRESH = 0.691
    ce_factor = 1 - penalty * np.clip(eji_s / EJI_THRESH, 0, 1)
    result[flagged] = result[flagged] * ce_factor[flagged]
    return result

esi_s1 = make_esi(3/7, 2/7, 2/7)
ofi_s1 = make_ofi()

print(f"  ESI S1 — mean: {np.nanmean(esi_s1[eligible_mask]):.3f}  "
      f"std: {np.nanstd(esi_s1[eligible_mask]):.3f}")
print(f"  OFI S1 — mean: {np.nanmean(ofi_s1[eligible_mask]):.3f}  "
      f"std: {np.nanstd(ofi_s1[eligible_mask]):.3f}")


# ── Stage 3: Compute S2–S5 ────────────────────────────────────────────────────

print("\n=== Stage 3: Scenarios S2–S5 ===")

scenarios = {
    # S2: Environment-first  (ESI 0.70, OFI 0.30)
    "S2": {
        "label": "S2 Environment-first",
        "esi": make_esi(3/7, 2/7, 2/7),   # same internal ESI weights
        "ofi": ofi_s1,
        "w_esi": 0.70,
        "eji_penalty": None,
        "fname": "gric_s2_envfirst_1km.tif",
    },
    # S3: Development-first  (ESI 0.30, OFI 0.70)
    "S3": {
        "label": "S3 Development-first",
        "esi": make_esi(3/7, 2/7, 2/7),
        "ofi": ofi_s1,
        "w_esi": 0.30,
        "eji_penalty": None,
        "fname": "gric_s3_devfirst_1km.tif",
    },
    # S4: Community-protective (ESI 0.60, OFI 0.40 + EJI penalty 0.75)
    "S4": {
        "label": "S4 Community-protective",
        "esi": make_esi(3/7, 2/7, 2/7),
        "ofi": ofi_s1,
        "w_esi": 0.60,
        "eji_penalty": 0.75,
        "fname": "gric_s4_commprot_1km.tif",
    },
    # S5: Conservation-weighted (ESI 0.75, OFI 0.25; water 4/6, wildfire 1/6, flood 1/6)
    "S5": {
        "label": "S5 Conservation-weighted",
        "esi": make_esi(4/6, 1/6, 1/6),   # water-dominant ESI
        "ofi": ofi_s1,
        "w_esi": 0.75,
        "eji_penalty": None,
        "fname": "gric_s5_conserv_1km.tif",
    },
}

computed = {}

for key, sc in scenarios.items():
    print(f"\n  Computing {sc['label']}...")
    gric_sc = make_gric_surface(sc["esi"], sc["ofi"], sc["w_esi"])

    if sc["eji_penalty"] is not None:
        gric_sc = apply_eji_penalty(gric_sc, penalty=sc["eji_penalty"])
        print(f"    EJI penalty {sc['eji_penalty']} applied.")

    out_path = f"{RDIR}/{sc['fname']}"
    write_raster(gric_sc, out_path)

    # Stats on eligible cells
    flat = gric_sc[eligible_mask]
    flat = flat[~np.isnan(flat)]
    print(f"    Valid cells: {len(flat):,}  mean: {np.mean(flat):.3f}  "
          f"std: {np.std(flat):.3f}  p90: {np.percentile(flat,90):.3f}")
    computed[key] = gric_sc


# ── Stage 4: Robustness — Jaccard top-decile vs S1 ───────────────────────────

print("\n=== Stage 4: Robustness (Jaccard top-decile overlap vs S1) ===")

# Reference: S1 top-decile cells
gric_s1_flat_vals = gric_s1[eligible_mask]
gric_s1_flat_vals = gric_s1_flat_vals[~np.isnan(gric_s1_flat_vals)]
q90_s1 = np.percentile(gric_s1_flat_vals, 90)
top_s1 = (gric_s1 >= q90_s1) & eligible_mask & ~np.isnan(gric_s1)

# State-level top-decile shares — load county/states layer
try:
    states_raster = read_raster(f"{RDIR}/mask_7states_1km_EPSG5070.tif")
except:
    states_raster = None

jaccard_results = {}
print(f"\n  S1 top-decile cells: {top_s1.sum():,} (q90={q90_s1:.3f})")

all_scenario_names = ["S1"] + list(computed.keys())
all_surfaces = {"S1": gric_s1, **computed}

print(f"\n  {'Scenario':<30} {'Top-decile cells':>17} {'Jaccard vs S1':>14} {'Median':>8} {'P90':>8}")
print("  " + "-"*82)

for sname in all_scenario_names:
    surf = all_surfaces[sname]
    flat = surf[eligible_mask & ~np.isnan(surf)]
    q90 = np.percentile(flat, 90)
    top = (surf >= q90) & eligible_mask & ~np.isnan(surf)
    n_top = top.sum()

    if sname == "S1":
        j = 1.0
    else:
        inter = np.sum(top & top_s1)
        union = np.sum(top | top_s1)
        j = float(inter / union) if union > 0 else 0.0

    label = sc["label"] if sname != "S1" else "S1 Balanced (reference)"
    if sname == "S1":
        label = "S1 Balanced (reference)"
    else:
        label = scenarios[sname]["label"]

    median_v = float(np.median(flat))
    p90_v    = float(np.percentile(flat, 90))

    print(f"  {label:<30} {n_top:>17,} {j:>13.3f}  {median_v:>7.3f}  {p90_v:>7.3f}")
    jaccard_results[sname] = {"jaccard_vs_s1": round(j, 3), "n_top_decile": int(n_top),
                               "p90_threshold": round(float(q90), 3)}


# ── Stage 5: State-level share of top-decile cells (S1–S5) ──────────────────

print("\n=== Stage 5: State top-decile shares across scenarios ===")

# Use the states7 vector — approximate by checking which cells are in each state
# We'll use the existing mask file — state separation isn't in a raster directly,
# so we'll work with the county GPKG via a bounding-box approach in a quick lookup.
# For the table, pull DC validation file which has State field.

# Simple approach: use the 7-state mask plus known approximate bounding boxes in EPSG:5070
# These are conservative estimates from the study area extent
STATE_BBOX = {
    # State: (col_min, col_max, row_min, row_max) in raster coordinates
    # Derived from approximate EPSG:5070 state extents
    "AZ": (-1600000, -800000, 770000,  1400000),   # lon/lat → EPSG:5070 approx
    "IL": ( 500000,  900000, 1580000, 1900000),
    "IA": ( 200000,  800000, 1800000, 2100000),
    "OR": (-2200000,-1000000, 2200000, 2800000),
    "TX": (-700000,  500000,  600000, 1400000),
    "VA": (1200000, 1791000, 1200000, 1600000),
    "WV": (1050000, 1450000, 1300000, 1650000),
}

def epsg5070_to_rc(x, y):
    col = int((x - XMIN) / RES)
    row = int(NROWS - 1 - (y - YMIN) / RES)
    return row, col

print(f"\n  {'State':<6}", end="")
for sname in all_scenario_names:
    print(f"  {sname:>8}", end="")
print()
print("  " + "-" * (6 + len(all_scenario_names) * 10))

state_results = {}
for state, (xmin_s, xmax_s, ymin_s, ymax_s) in STATE_BBOX.items():
    r1, c1 = epsg5070_to_rc(xmin_s, ymax_s)
    r2, c2 = epsg5070_to_rc(xmax_s, ymin_s)
    r1 = max(0, min(r1, r2)); r2 = min(NROWS-1, max(r1, r2)+1)
    c1 = max(0, min(c1, c2)); c2 = min(NCOLS-1, max(c1, c2)+1)
    state_mask = np.zeros((NROWS, NCOLS), dtype=bool)
    state_mask[r1:r2, c1:c2] = True
    state_mask &= eligible_mask

    print(f"  {state:<6}", end="")
    state_results[state] = {}
    for sname in all_scenario_names:
        surf = all_surfaces[sname]
        flat_all = surf[eligible_mask & ~np.isnan(surf)]
        q90 = np.percentile(flat_all, 90)
        top = (surf >= q90) & state_mask & ~np.isnan(surf)
        n_state_elig = state_mask.sum()
        share = float(top.sum() / n_state_elig * 100) if n_state_elig > 0 else 0.0
        print(f"  {share:>7.1f}%", end="")
        state_results[state][sname] = round(share, 1)
    print()


# ── Stage 6: Task 3 — Confidence layer stats ─────────────────────────────────

print("\n=== Stage 6: Confidence layer stats (Task 3) ===")

conf_elig = confidence[eligible_mask & ~np.isnan(confidence)]
median_conf = float(np.median(conf_elig))
low_conf_share = float(np.mean(conf_elig < 0.40) * 100)
high_conf_share = float(np.mean(conf_elig >= 0.60) * 100)

print(f"  Valid confidence cells: {len(conf_elig):,}")
print(f"  Median confidence:      {median_conf:.3f}")
print(f"  Share low (<0.40):      {low_conf_share:.1f}%")
print(f"  Share high (≥0.60):     {high_conf_share:.1f}%")
print(f"  Min / Max:              {conf_elig.min():.3f} / {conf_elig.max():.3f}")

# Confidence by tertile of GRIC score
gric_flat = gric_s1[eligible_mask & ~np.isnan(gric_s1) & ~np.isnan(confidence)]
conf_flat  = confidence[eligible_mask & ~np.isnan(gric_s1) & ~np.isnan(confidence)]
q33 = np.percentile(gric_flat, 33); q67 = np.percentile(gric_flat, 67)
for label, mask_t in [("Low GRIC (bottom 1/3)", gric_flat < q33),
                       ("Mid GRIC (middle 1/3)", (gric_flat >= q33) & (gric_flat < q67)),
                       ("High GRIC (top 1/3)",   gric_flat >= q67)]:
    c_t = conf_flat[mask_t]
    print(f"  {label}: median conf = {np.median(c_t):.3f}  low-conf share = {np.mean(c_t<0.40)*100:.1f}%")


# ── Stage 7: Save all results ─────────────────────────────────────────────────

print("\n=== Stage 7: Saving results ===")

out = {
    "scenarios": {k: {"jaccard_vs_s1": v["jaccard_vs_s1"],
                      "n_top_decile": v["n_top_decile"],
                      "p90_threshold": v["p90_threshold"]}
                  for k, v in jaccard_results.items()},
    "state_top_decile_shares": state_results,
    "confidence": {
        "median": round(median_conf, 3),
        "low_share_pct": round(low_conf_share, 1),
        "high_share_pct": round(high_conf_share, 1),
    }
}

with open(f"{BASE}/00_ADMIN/scenario_robustness.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"  → scenario_robustness.json")

print("\n=== DONE ===")
print("\nRasters written to 11_processed_layers/rasters/:")
for sc in scenarios.values():
    print(f"  {sc['fname']}")
