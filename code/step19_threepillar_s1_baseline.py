#!/usr/bin/env python3
"""
step19_threepillar_s1_baseline.py
----------------------------------
Run with:  ./gis_venv/bin/python3 step19_threepillar_s1_baseline.py

Builds the revised 3-pillar GRIC baseline (S1):

  GRIC = ESI × 0.333 + OFI × 0.333 + SII × 0.333

  ESI (site risk — what threatens the DC):
    water_stress_current  × 0.333   Aqueduct BWS 2010 baseline
    nri_eal_buildings     × 0.333   FEMA NRI EAL 18-hazard composite (EAL_SPCTL)
    cmip6_heat            × 0.333   NEX-GDDP mean heat days >35°C, 2041-2060

  OFI (infrastructure — what the site provides):
    tx_230kV              × 0.611   ROC rank 1  (power)
    ixp_proximity         × 0.278   ROC rank 2  (connectivity)
    roads_proximity       × 0.111   ROC rank 3  (access)

  SII (sustainability impact — what the DC does to the place):
    carbon_co2e           × 0.333   eGRID 2023 CO2e intensity
    eji_burden            × 0.333   CDC EJI 2024 rpl_eji (inverted)
    water_stress_future   × 0.333   Aqueduct 2050 BAU projected stress

M0 hard exclusions: PAD-US GAP1+2, NFHL SFHA, NLCD ineligible, NLCD water.

Outputs (all in 11_processed_layers/rasters/):
    nri_eal_buildings_suitability_1km.tif
    cmip6_heat_suitability_1km.tif
    tx_230kV_suitability_1km.tif
    roads_suitability_1km.tif
    eji_suitability_1km.tif
    esi_composite_1km.tif
    ofi_composite_1km.tif
    sii_composite_1km.tif
    gric_s1_threepillar_1km.tif
    00_ADMIN/gric_threepillar_s1_summary.json
"""

import os, json, subprocess
import numpy as np

# ── Environment ─────────────────────────────────────────────────────────────
PROJ_ENV = {
    **os.environ,
    "PROJ_LIB":  "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj",
    "GDAL_DATA": "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal",
}
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"

# ── Grid constants ───────────────────────────────────────────────────────────
NROWS, NCOLS = 2597, 4086
XMIN, YMIN   = -2295000, 310000
RES          = 1000
XMAX         = XMIN + NCOLS * RES   # 1791000
YMAX         = YMIN + NROWS * RES   # 2907000

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RDIR = f"{BASE}/11_processed_layers/rasters"
VDIR = f"{BASE}/11_processed_layers"
ADM  = f"{BASE}/00_ADMIN"

# State bounding boxes (EPSG:5070 x0,y0,x1,y1)
STATES = {
    # Derived from NRI county extents in EPSG:5070 + 50 km buffer
    "AZ": (-1800000,  950000, -1100000, 1750000),
    "IL": (  330000, 1520000,   780000, 2240000),
    "IA": ( -100000, 1890000,   540000, 2340000),
    "OR": (-2295000, 2250000, -1530000, 2907000),
    "TX": (-1050000,  260000,   290000, 1570000),
    "VA": ( 1040000, 1530000,  1840000, 2020000),
    "WV": ( 1100000, 1620000,  1600000, 2110000),
}

# ── I/O helpers ──────────────────────────────────────────────────────────────
def run(cmd, desc=""):
    r = subprocess.run(cmd, env=PROJ_ENV, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ERROR ({desc or cmd[0]}): {r.stderr[-600:]}")
        raise RuntimeError(r.stderr)
    return r.stdout


def read_raster(tif):
    tmp = tif + ".tmp19.raw"
    run([f"{GDAL_BIN}/gdal_translate", "-of", "ENVI", "-ot", "Float32",
         "-co", "INTERLEAVE=BSQ", tif, tmp], f"read {os.path.basename(tif)}")
    arr = np.fromfile(tmp, dtype=np.float32).reshape(NROWS, NCOLS)
    for f in [tmp, tmp + ".hdr"]:
        try: os.remove(f)
        except: pass
    arr = arr.astype(np.float64)
    arr[(arr == -9999.0) | (arr == -9998.0) | (arr == 255.0)] = np.nan
    return arr


def write_raster(arr, path):
    tmp_raw = path + ".tmp19.raw"
    tmp_vrt = path + ".tmp19.vrt"
    a32 = arr.astype(np.float32)
    a32[np.isnan(arr)] = -9999.0
    a32.tofile(tmp_raw)
    hdr = (f"ENVI\nsamples = {NCOLS}\nlines = {NROWS}\nbands = 1\n"
           f"header offset = 0\nfile type = ENVI Standard\ndata type = 4\n"
           f"interleave = bsq\nbyte order = 0\n")
    with open(tmp_raw + ".hdr", "w") as f:
        f.write(hdr)
    vrt_xml = f"""<VRTDataset rasterXSize="{NCOLS}" rasterYSize="{NROWS}">
  <SRS>EPSG:5070</SRS>
  <GeoTransform>{XMIN}, {RES}, 0, {YMAX}, 0, -{RES}</GeoTransform>
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
         tmp_vrt, path], f"write {os.path.basename(path)}")
    for f in [tmp_raw, tmp_raw + ".hdr", tmp_vrt]:
        try: os.remove(f)
        except: pass
    print(f"  Written: {os.path.basename(path)}")


def stats(arr, label):
    v = arr[~np.isnan(arr)]
    if v.size == 0:
        print(f"  {label}: ALL NoData")
        return
    print(f"  {label}: n={v.size:,}  "
          f"min={v.min():.4f}  mean={v.mean():.4f}  max={v.max():.4f}")


def state_mean(arr, state, mask_bin):
    x0, y0, x1, y1 = STATES[state]
    col0 = max(0, int((x0 - XMIN) / RES))
    col1 = min(NCOLS, int((x1 - XMIN) / RES))
    row0 = max(0, int((YMAX - y1) / RES))
    row1 = min(NROWS, int((YMAX - y0) / RES))
    sub  = arr[row0:row1, col0:col1]
    msk  = mask_bin[row0:row1, col0:col1]
    vals = sub[(msk == 1) & ~np.isnan(sub)]
    return float(np.nanmean(vals)) if vals.size > 0 else np.nan


def pillar(weighted_layers):
    """Weighted mean; excludes NaN inputs from weight denominator."""
    acc = np.zeros((NROWS, NCOLS), dtype=np.float64)
    tw  = np.zeros((NROWS, NCOLS), dtype=np.float64)
    for w, arr in weighted_layers:
        valid = ~np.isnan(arr)
        acc[valid] += w * arr[valid]
        tw[valid]  += w
    result = np.where(tw > 0, acc / tw, np.nan)
    return result


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("SECTION 1: Building suitability rasters")
print("="*60)

mask_raw = read_raster(f"{RDIR}/mask_7states_1km_EPSG5070.tif")
# Mask stores 1=valid 7-state cell, 0=outside. Do NOT use nan test — 0 is real.
mask_bin = (mask_raw == 1).astype(np.float64)

# ── 1a. NRI EAL Buildings — rasterize EAL_SPCTL, then invert ───────────────
NRI_GPKG = f"{VDIR}/fema_nri_counties_EPSG5070.gpkg"
EAL_RAW  = f"{RDIR}/_nri_eal_spctl_tmp.tif"
NRI_OUT  = f"{RDIR}/nri_eal_buildings_suitability_1km.tif"

print("\n[1a] NRI EAL Buildings composite (rasterising EAL_SPCTL)")
run([
    f"{GDAL_BIN}/gdal_rasterize",
    "-a", "EAL_SPCTL",
    "-l", "fema_nri_counties",
    "-tr", str(RES), str(RES),
    "-te", str(XMIN), str(YMIN), str(XMAX), str(YMAX),
    "-a_nodata", "-9999",
    "-ot", "Float32",
    "-co", "COMPRESS=LZW", "-co", "TILED=YES",
    NRI_GPKG, EAL_RAW,
], "NRI rasterize")

eal_raw = read_raster(EAL_RAW)
os.remove(EAL_RAW)

# EAL_SPCTL: 0-100 national percentile. Higher = more loss = lower suitability.
eal_suit = np.where(np.isnan(eal_raw), np.nan,
                    1.0 - np.clip(eal_raw / 100.0, 0.0, 1.0))
eal_suit[mask_bin == 0] = np.nan
write_raster(eal_suit, NRI_OUT)
stats(eal_suit, "NRI EAL suitability")

# ── 1b. CMIP6 heat suitability (invert heat days, min-max) ─────────────────
HEAT_OUT = f"{RDIR}/cmip6_heat_suitability_1km.tif"
print("\n[1b] CMIP6 heat days suitability")
heat_raw  = read_raster(f"{RDIR}/nexgddp_mean_days_gt35_2041_2060.tif")
heat_max  = float(np.nanmax(heat_raw))
heat_suit = np.where(np.isnan(heat_raw), np.nan,
                     1.0 - np.clip(heat_raw / heat_max, 0.0, 1.0))
heat_suit[mask_bin == 0] = np.nan
write_raster(heat_suit, HEAT_OUT)
stats(heat_suit, "CMIP6 heat suitability")
print(f"     Normalisation cap: {heat_max:.1f} days (observed 7-state max)")

# ── 1c. 230kV proximity suitability (cap at 500 km) ────────────────────────
TX_OUT = f"{RDIR}/tx_230kV_suitability_1km.tif"
TX_CAP = 500_000.0
print("\n[1c] 230kV transmission proximity suitability")
tx_raw  = read_raster(f"{RDIR}/hifld_tx_230kV_proximity_1km.tif")
tx_suit = np.where(np.isnan(tx_raw), np.nan,
                   1.0 - np.clip(tx_raw / TX_CAP, 0.0, 1.0))
tx_suit[mask_bin == 0] = np.nan
write_raster(tx_suit, TX_OUT)
stats(tx_suit, "230kV suitability")

# ── 1d. Roads proximity suitability (cap at 100 km) ────────────────────────
RD_OUT = f"{RDIR}/roads_suitability_1km.tif"
RD_CAP = 100_000.0
print("\n[1d] Roads proximity suitability (primary + secondary)")
rd_raw  = read_raster(f"{RDIR}/tiger_roads_prisec_proximity_1km.tif")
rd_suit = np.where(np.isnan(rd_raw), np.nan,
                   1.0 - np.clip(rd_raw / RD_CAP, 0.0, 1.0))
rd_suit[mask_bin == 0] = np.nan
write_raster(rd_suit, RD_OUT)
stats(rd_suit, "Roads suitability")
print(f"     Max observed distance: {np.nanmax(rd_raw)/1000:.1f} km  (cap: 100 km)")

# ── 1e. EJI suitability (invert rpl_eji burden score) ──────────────────────
EJI_OUT = f"{RDIR}/eji_suitability_1km.tif"
print("\n[1e] EJI suitability (burden inverted: 1 − rpl_eji)")
eji_raw  = read_raster(f"{RDIR}/eji_2024_score_1km.tif")
eji_suit = np.where(np.isnan(eji_raw), np.nan,
                    1.0 - np.clip(eji_raw, 0.0, 1.0))
eji_suit[mask_bin == 0] = np.nan
write_raster(eji_suit, EJI_OUT)
stats(eji_suit, "EJI suitability (inverted)")


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("SECTION 2: Loading all suitability layers")
print("="*60)

layers = {
    # ESI
    "water_current": read_raster(f"{RDIR}/water_stress_baseline_bws_suitability.tif"),
    "nri_eal":       read_raster(NRI_OUT),
    "cmip6_heat":    read_raster(HEAT_OUT),
    # OFI
    "tx_230kV":      read_raster(TX_OUT),
    "ixp":           read_raster(f"{RDIR}/ixp_proximity_suitability_1km.tif"),
    "roads":         read_raster(RD_OUT),
    # SII
    "carbon_co2e":   read_raster(f"{RDIR}/carbon_current_co2e_suitability.tif"),
    "eji":           read_raster(EJI_OUT),
    "water_future":  read_raster(f"{RDIR}/water_stress_future2050bau_ws_suitability.tif"),
}

print("\n  Layer validity:")
for name, arr in layers.items():
    n = int(np.sum(~np.isnan(arr)))
    print(f"    {name:<20} n={n:>9,}  "
          f"min={np.nanmin(arr):.3f}  mean={np.nanmean(arr):.3f}  max={np.nanmax(arr):.3f}")


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("SECTION 3: Pillar composites")
print("="*60)

# ESI — equal weights (chronic / acute physical / future climate: incommensurable)
esi = pillar([(1/3, layers["water_current"]),
              (1/3, layers["nri_eal"]),
              (1/3, layers["cmip6_heat"])])
esi[mask_bin == 0] = np.nan
write_raster(esi, f"{RDIR}/esi_composite_1km.tif")
stats(esi, "ESI composite")

# OFI — ROC weights (power > connectivity > access)
ofi = pillar([(0.611, layers["tx_230kV"]),
              (0.278, layers["ixp"]),
              (0.111, layers["roads"])])
ofi[mask_bin == 0] = np.nan
write_raster(ofi, f"{RDIR}/ofi_composite_1km.tif")
stats(ofi, "OFI composite")

# SII — equal weights (climate / equity / hydrological: incommensurable)
sii = pillar([(1/3, layers["carbon_co2e"]),
              (1/3, layers["eji"]),
              (1/3, layers["water_future"])])
sii[mask_bin == 0] = np.nan
write_raster(sii, f"{RDIR}/sii_composite_1km.tif")
stats(sii, "SII composite")


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("SECTION 4: GRIC composite (equal pillar weights)")
print("="*60)

gric_raw = pillar([(1/3, esi), (1/3, ofi), (1/3, sii)])
gric_raw[mask_bin == 0] = np.nan
stats(gric_raw, "GRIC (pre-exclusion)")


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("SECTION 5: M0 hard exclusions")
print("="*60)

gric = gric_raw.copy()
excl_count = {}

def apply_excl(label, path, condition_fn):
    arr  = read_raster(path)
    mask = condition_fn(arr) & (~np.isnan(gric))
    n    = int(mask.sum())
    excl_count[label] = n
    gric[mask] = np.nan
    print(f"  {label:<38} excluded {n:>8,} cells")

apply_excl("PAD-US GAP 1+2",
           f"{RDIR}/pad_us_gap12_exclusion_1km.tif",
           lambda a: a == 1)

apply_excl("NFHL SFHA any-overlap",
           f"{RDIR}/nfhl_sfha_exclusion_1km.tif",
           lambda a: a == 1)

apply_excl("NLCD eligible < 10%",
           f"{RDIR}/pct_eligible_1km_EPSG5070.tif",
           lambda a: (~np.isnan(a)) & (a < 0.10))

apply_excl("NLCD water/wetland >= 50%",
           f"{RDIR}/pct_waterwetland_1km_EPSG5070.tif",
           lambda a: (~np.isnan(a)) & (a >= 0.50))

n_viable = int(np.sum(~np.isnan(gric)))
print(f"\n  Viable cells after exclusions: {n_viable:,}")
stats(gric, "GRIC S1 (post-exclusion)")

write_raster(gric, f"{RDIR}/gric_s1_threepillar_1km.tif")


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("SECTION 6: Per-state statistics")
print("="*60)

pillar_map = {"ESI": esi, "OFI": ofi, "SII": sii, "GRIC": gric}
results    = {}

print(f"\n  {'State':<5}  {'GRIC':>6}  {'ESI':>6}  {'OFI':>6}  {'SII':>6}")
print("  " + "-"*40)
for state in ["AZ","IL","IA","OR","TX","VA","WV"]:
    row = {k: round(state_mean(v, state, mask_bin), 4) for k, v in pillar_map.items()}
    results[state] = row
    print(f"  {state}    {row['GRIC']:>6.4f}  {row['ESI']:>6.4f}  "
          f"{row['OFI']:>6.4f}  {row['SII']:>6.4f}")

crit_keys = [
    ("water_current","WatCur"),("nri_eal","NRI_EAL"),("cmip6_heat","Heat"),
    ("tx_230kV","TX230"),("ixp","IXP"),("roads","Roads"),
    ("carbon_co2e","CO2e"),("eji","EJI"),("water_future","WatFut"),
]
print(f"\n  {'State':<5}  " + "  ".join(f"{h:>7}" for _,h in crit_keys))
print("  " + "-"*80)
for state in ["AZ","IL","IA","OR","TX","VA","WV"]:
    vals = [f"{state_mean(layers[k], state, mask_bin):>7.4f}" for k,_ in crit_keys]
    print(f"  {state}    " + "  ".join(vals))


# ── JSON summary ─────────────────────────────────────────────────────────────
summary = {
    "model": {
        "name": "GRIC_S1_ThreePillar",
        "pillar_weights": {"ESI": 0.333, "OFI": 0.333, "SII": 0.333},
        "ESI": {
            "weights": {"water_stress_current": 0.333, "nri_eal_buildings": 0.333, "cmip6_heat": 0.333},
            "justification": "equal: incommensurable risk types (chronic / acute / future)",
            "sources": {
                "water_stress_current": "WRI Aqueduct 4.0 BWS 2010 baseline",
                "nri_eal_buildings":    "FEMA NRI 2023 EAL_SPCTL 18-hazard composite",
                "cmip6_heat":           "NEX-GDDP-CMIP6 mean days >35C 2041-2060 (normalised to 7-state max)",
            }
        },
        "OFI": {
            "weights": {"tx_230kV": 0.611, "ixp": 0.278, "roads": 0.111},
            "justification": "ROC rank-order centroid: power > connectivity > access (literature-supported)",
            "caps_km": {"tx_230kV": 500, "ixp": 500, "roads": 100},
        },
        "SII": {
            "weights": {"carbon_co2e": 0.333, "eji_burden": 0.333, "water_stress_future": 0.333},
            "justification": "equal: incommensurable impact types (climate / equity / hydrological) — Munda (2004)",
            "sources": {
                "carbon_co2e":         "eGRID 2023 annual CO2e lb/MWh (inverted suitability)",
                "eji_burden":          "CDC EJI 2024 rpl_eji (inverted: 1 − burden percentile)",
                "water_stress_future": "WRI Aqueduct 4.0 BAU 2050 projected stress (inverted)",
            }
        },
        "exclusions": {
            "pad_us_gap12": "binary = 1",
            "nfhl_sfha":    "any overlap = 1",
            "nlcd_eligible": "< 0.10",
            "nlcd_water":   ">= 0.50",
        }
    },
    "viable_cells": n_viable,
    "exclusion_counts": excl_count,
    "state_means": results,
}

out_json = f"{ADM}/gric_threepillar_s1_summary.json"
with open(out_json, "w") as f:
    json.dump(summary, f, indent=2)
print(f"\n  Summary written → {out_json}")

print("\n" + "="*60)
print("DONE — step19 complete")
print("="*60)
