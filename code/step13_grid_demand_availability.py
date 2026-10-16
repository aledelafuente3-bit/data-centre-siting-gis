#!/usr/bin/env python3
"""
step13_grid_demand_availability.py
Grid Demand & Availability (GDA) module — two suitability rasters at 1 km.

Run with QGIS Python:
  PROJ_LIB=".../share/proj" GDAL_DATA=".../share/gdal" \
  /Applications/QGIS-LTR.app/Contents/MacOS/bin/python3 step13_grid_demand_availability.py

Source: BA polygon layer (HIFLD, 2020 snapshot):
  11_processed_layers/ba_with_co2e_EPSG5070.gpkg
  Fields used: PEAK_LOAD (MW, 2020 summer peak), TOTAL_CAP (MW nameplate), NAME (BA code)

Outputs (EPSG:5070, 1 km, LZW GeoTIFF — context/supplementary layers, not in GRIC baseline):
  gda_reserve_margin_suit_1km.tif
      (TOTAL_CAP − PEAK_LOAD) / TOTAL_CAP normalised to [10%, 40%]
      Higher = more grid headroom available for new large loads
  gda_utilization_suit_1km.tif
      1 − (PEAK_LOAD / TOTAL_CAP)
      Higher = grid is less loaded relative to capacity = better siting

Note on CAGR: EIA-861 2024 BA-level demand data could not be reliably aggregated
(major ISOs — ERCO, PJM, MISO — are not individually represented in the
Balancing_Authority_2024.xlsx utility crosswalk). CAGR layer deferred to future work.
"""

import os, sys, json, shutil, subprocess
import numpy as np
from osgeo import ogr, gdal

ogr.UseExceptions()
gdal.UseExceptions()

BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
PROJ_ENV = {**os.environ,
            "PROJ_LIB":  "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj",
            "GDAL_DATA": "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"}

RASTER_DIR = f"{BASE}/11_processed_layers/rasters"
BA_GPKG    = f"{BASE}/11_processed_layers/ba_with_co2e_EPSG5070.gpkg"
MASK_TIF   = f"{RASTER_DIR}/mask_7states_1km_EPSG5070.tif"

XMIN, YMIN, XMAX, YMAX = -2295000, 310000, 1791000, 2907000
RES = 1000
NCOLS, NROWS = 4086, 2597
ND = -9999.0

RM_LOW,  RM_HIGH  = 0.10, 0.40   # reserve margin norm bounds
MIN_CAP = 100                     # ignore BAs with TOTAL_CAP ≤ 100 MW (bad/zero data)


# ── helpers ──────────────────────────────────────────────────────────────────

def run(cmd):
    r = subprocess.run(cmd, env=PROJ_ENV, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n{r.stderr}")


def gdal_rasterize(src_gpkg, layer, field, out_tif):
    if os.path.exists(out_tif):
        os.remove(out_tif)
    run([f"{GDAL_BIN}/gdal_rasterize",
         "-l", layer, "-a", field,
         "-tr", str(RES), str(RES),
         "-te", str(XMIN), str(YMIN), str(XMAX), str(YMAX),
         "-a_nodata", str(ND), "-ot", "Float32",
         "-co", "COMPRESS=LZW", "-co", "TILED=YES",
         src_gpkg, out_tif])
    print(f"  → {os.path.basename(out_tif)}")


def read_raster(tif):
    tmp = tif + ".tmp.raw"
    run([f"{GDAL_BIN}/gdal_translate", "-of", "ENVI", "-ot", "Float32",
         "-co", "INTERLEAVE=BSQ", tif, tmp])
    arr = np.fromfile(tmp, dtype=np.float32).reshape(NROWS, NCOLS)
    for f in [tmp, tmp + ".hdr"]:
        try: os.remove(f)
        except: pass
    return arr


# ── Stage 1: Read BA polygon layer, compute metrics ──────────────────────────

print("\n=== Stage 1: Load BA polygons and compute metrics ===")

ds = ogr.Open(BA_GPKG, 0)
lyr = ds.GetLayer(0)

rows = []
for feat in lyr:
    peak = feat.GetField("PEAK_LOAD")
    cap  = feat.GetField("TOTAL_CAP")
    name = feat.GetField("NAME")
    rows.append({"name": name, "peak": peak, "cap": cap})
ds = None

print(f"\n{'BA':40s} {'PEAK_MW':>9} {'CAP_MW':>9} {'RM%':>7} {'RM_SUIT':>8} {'UTIL':>6} {'U_SUIT':>7} {'STATUS'}")
print("-" * 105)

metrics = {}   # name → {rm_suit, util_suit}
for r in rows:
    peak, cap, name = r["peak"], r["cap"], r["name"]
    # Skip bad data: negative placeholders, zero cap, or None
    if cap is None or peak is None or cap <= MIN_CAP or peak <= 0:
        status = "SKIP (no data)"
        print(f"{name[:40]:40s} {str(peak):>9} {str(cap):>9} {'':>7} {'':>8} {'':>6} {'':>7} {status}")
        metrics[name] = {"rm_suit": ND, "util_suit": ND}
        continue
    rm       = (cap - peak) / cap
    util     = peak / cap
    rm_suit  = float(np.clip((rm  - RM_LOW) / (RM_HIGH - RM_LOW), 0.0, 1.0))
    util_suit = float(np.clip(1.0 - util, 0.0, 1.0))
    status   = "✓" if rm > 0 else "⚠ overloaded"
    print(f"{name[:40]:40s} {peak:>9,.0f} {cap:>9,.0f} {rm*100:>6.1f}% "
          f"{rm_suit:>8.3f} {util:>6.3f} {util_suit:>7.3f} {status}")
    metrics[name] = {"rm_suit": rm_suit, "util_suit": util_suit}


# ── Stage 2: Write metrics to temp GPKG ──────────────────────────────────────

print("\n=== Stage 2: Write metrics to temp GPKG ===")

tmp_gpkg = f"{BASE}/11_processed_layers/gda_temp_metrics.gpkg"
if os.path.exists(tmp_gpkg):
    os.remove(tmp_gpkg)
shutil.copy(BA_GPKG, tmp_gpkg)

ds = ogr.Open(tmp_gpkg, 1)
lyr = ds.GetLayer(0)

for field_name in ["rm_suit", "util_suit"]:
    fd = ogr.FieldDefn(field_name, ogr.OFTReal)
    lyr.CreateField(fd)

updated = skipped = 0
for feat in lyr:
    name = feat.GetField("NAME")
    m = metrics.get(name, {"rm_suit": ND, "util_suit": ND})
    feat.SetField("rm_suit",   float(m["rm_suit"]))
    feat.SetField("util_suit", float(m["util_suit"]))
    lyr.SetFeature(feat)
    if m["rm_suit"] != ND:
        updated += 1
    else:
        skipped += 1

ds = None
print(f"  {updated} BAs with valid metrics | {skipped} BAs set to NoData")


# ── Stage 3: Rasterize ───────────────────────────────────────────────────────

print("\n=== Stage 3: Rasterize to 1 km ===")

lyr_name = "ba_with_co2e"
outputs  = {
    "gda_reserve_margin_suit_1km.tif": "rm_suit",
    "gda_utilization_suit_1km.tif":    "util_suit",
}
for fname, field in outputs.items():
    gdal_rasterize(tmp_gpkg, lyr_name, field, f"{RASTER_DIR}/{fname}")

os.remove(tmp_gpkg)


# ── Stage 4: Stats within 7-state mask ───────────────────────────────────────

print("\n=== Stage 4: Stats within 7-state mask ===")

mask  = read_raster(MASK_TIF)
mask7 = (mask == 1)
n_mask = int(mask7.sum())
print(f"  Mask cells: {n_mask:,}")

summary = {}
for fname in outputs:
    arr   = read_raster(f"{RASTER_DIR}/{fname}")
    in_m  = arr[mask7]
    valid = in_m[(in_m != ND) & ~np.isnan(in_m)]
    nd_pct = (np.sum((in_m == ND) | np.isnan(in_m)) / n_mask) * 100

    print(f"\n  {fname}:")
    print(f"    valid cells : {len(valid):,}  |  NoData within mask: {nd_pct:.1f}%")
    if len(valid):
        p25, p75 = float(np.percentile(valid, 25)), float(np.percentile(valid, 75))
        print(f"    min / mean / median / max : "
              f"{valid.min():.3f} / {valid.mean():.3f} / "
              f"{np.median(valid):.3f} / {valid.max():.3f}")
        print(f"    p25 / p75   : {p25:.3f} / {p75:.3f}")

        # Show which BAs are represented in each range
        top_cells    = np.sum(valid >= 0.667)
        mid_cells    = np.sum((valid >= 0.333) & (valid < 0.667))
        bottom_cells = np.sum(valid < 0.333)
        print(f"    High suit (≥0.667): {top_cells:,} cells ({top_cells/len(valid)*100:.1f}%)")
        print(f"    Mid  suit (0.333–0.667): {mid_cells:,} cells ({mid_cells/len(valid)*100:.1f}%)")
        print(f"    Low  suit (<0.333): {bottom_cells:,} cells ({bottom_cells/len(valid)*100:.1f}%)")
    summary[fname] = {
        "n_valid": int(len(valid)),
        "nodata_pct_within_mask": round(float(nd_pct), 1),
        "min":    round(float(valid.min()), 3) if len(valid) else None,
        "mean":   round(float(valid.mean()), 3) if len(valid) else None,
        "median": round(float(np.median(valid)), 3) if len(valid) else None,
        "max":    round(float(valid.max()), 3) if len(valid) else None,
        "p25":    round(float(np.percentile(valid, 25)), 3) if len(valid) else None,
        "p75":    round(float(np.percentile(valid, 75)), 3) if len(valid) else None,
        "source": "HIFLD BA polygons 2020 (PEAK_LOAD, TOTAL_CAP fields)",
    }

with open(f"{BASE}/00_ADMIN/gda_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("\n=== DONE ===")
print("Files written to 11_processed_layers/rasters/:")
for fname in outputs:
    print(f"  {fname}")
print("\nNote: Both layers use 2020 HIFLD BA capacity/demand baseline.")
print("Summary → 00_ADMIN/gda_summary.json")
