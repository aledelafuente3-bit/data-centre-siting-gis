#!/usr/bin/env python3
"""
step8_build_qgis_review_project.py
Build QGIS review project for Minimum Additions QC

Output: 12_qgis_projects/working/DataCenter_Suitability_REVIEW_MINIMUM_ADDITIONS.qgz

Groups:
  00 — Study Area / Reference
  01 — Hard Exclusions  (PAD-US, NFHL, Slope, NLCD)
  02 — ESI — Environmental Stewardship
  03 — OFI — Operational Feasibility
  04 — Grid Readiness Screen
  05 — Community & Equity
  06 — Risk & Resilience / Uncertainty
  07 — Opportunity Overlay
  08 — Validation
  09 — Sensitivity / SAIDI Context
  10 — Legacy / Superseded

Rules:
  - EPSG:5070 project CRS
  - No /tmp paths
  - No composites, no weights
  - New file only — never overwrites DataCenter_Suitability_REVIEW_v3.qgz
"""

import os, sys

# ── QGIS bootstrap ───────────────────────────────────────────────────────────
os.environ["PROJ_LIB"]  = "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj"
os.environ["GDAL_DATA"] = "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"
QGIS_PYTHON = "/Applications/QGIS-LTR.app/Contents/MacOS/lib/python3.9/site-packages"
if QGIS_PYTHON not in sys.path:
    sys.path.insert(0, QGIS_PYTHON)

from qgis.core import (
    QgsApplication, QgsProject, QgsCoordinateReferenceSystem,
    QgsRasterLayer, QgsVectorLayer,
    QgsLayerTree, QgsLayerTreeGroup, QgsLayerTreeLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

QCoreApplication.setOrganizationName("QGIS")
app = QgsApplication([], False)
app.initQgis()

BASE  = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RAST  = f"{BASE}/11_processed_layers/rasters"
PROC  = f"{BASE}/11_processed_layers"
VAL   = f"{BASE}/06_VALIDATION"
OUT   = f"{BASE}/12_qgis_projects/working/DataCenter_Suitability_REVIEW_MINIMUM_ADDITIONS.qgz"

# Safety check — never overwrite the v3 original
if os.path.exists(OUT):
    print(f"  File already exists: {os.path.basename(OUT)}")
    print("  Will overwrite (this is the MINIMUM_ADDITIONS file, not v3)")

# ── Project setup ─────────────────────────────────────────────────────────────
project = QgsProject.instance()
project.clear()
crs = QgsCoordinateReferenceSystem("EPSG:5070")
project.setCrs(crs)
project.setTitle("Data Centre Siting — Minimum Additions QC Review (PAD-US / NFHL / Slope / Roads / EJI)")
print(f"  Project CRS: {project.crs().authid()}")

root = project.layerTreeRoot()

def add_raster(group, path, name, visible=True):
    """Add raster layer to group; skip if file missing."""
    if not os.path.exists(path):
        print(f"  SKIP (not found): {name}")
        return None
    lyr = QgsRasterLayer(path, name)
    if not lyr.isValid():
        print(f"  INVALID: {name} — {path}")
        return None
    project.addMapLayer(lyr, False)
    node = group.addLayer(lyr)
    node.setItemVisibilityChecked(visible)
    print(f"  ✅ {name}")
    return lyr

def add_vector(group, path, layername, display_name, visible=True):
    """Add vector layer (GPKG) to group; skip if file missing."""
    if not os.path.exists(path):
        print(f"  SKIP (not found): {display_name}")
        return None
    uri = f"{path}|layername={layername}" if layername else path
    lyr = QgsVectorLayer(uri, display_name, "ogr")
    if not lyr.isValid():
        print(f"  INVALID: {display_name} — {uri}")
        return None
    project.addMapLayer(lyr, False)
    node = group.addLayer(lyr)
    node.setItemVisibilityChecked(visible)
    print(f"  ✅ {display_name}")
    return lyr

def make_group(root, name, visible=True):
    g = root.addGroup(name)
    g.setItemVisibilityChecked(visible)
    return g

# ═══════════════════════════════════════════════════════════════════════════════
# 00 — Study Area / Reference
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 00 Study Area / Reference ---")
g00 = make_group(root, "00 — Study Area / Reference", visible=True)
add_raster(g00, f"{RAST}/mask_7states_1km_EPSG5070.tif",
           "7-State Mask (1km)", visible=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 01 — Hard Exclusions
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 01 Hard Exclusions ---")
g01 = make_group(root, "01 — Hard Exclusions", visible=True)

# PAD-US subgroup
g01_pad = g01.addGroup("PAD-US 4.0 Protected Areas")
add_raster(g01_pad, f"{RAST}/pad_us_gap12_exclusion_1km.tif",
           "PAD-US GAP 1+2 Exclusion [5.68%] ⛔", visible=True)
add_raster(g01_pad, f"{RAST}/pad_us_gap3_flag_1km.tif",
           "PAD-US GAP 3 Planning Review Flag [12.99%] ⚠️", visible=False)
add_vector(g01_pad, f"{PROC}/pad_us_40_gap12_EPSG5070.gpkg",
           "padus_gap12", "PAD-US GAP 1+2 Polygons (13,689 features)", visible=False)
add_vector(g01_pad, f"{PROC}/pad_us_40_gap3_EPSG5070.gpkg",
           "padus_gap3", "PAD-US GAP 3 Polygons (12,619 features)", visible=False)

# NFHL subgroup
g01_nfhl = g01.addGroup("NFHL Flood Hazard [⚠️ lower-bound IA/TX/VA]")
add_raster(g01_nfhl, f"{RAST}/nfhl_floodway_fraction_1km.tif",
           "NFHL Floodway Fraction (hard excl. if >0) ⛔", visible=True)
add_raster(g01_nfhl, f"{RAST}/nfhl_sfha_fraction_1km.tif",
           "NFHL SFHA Fraction (strict constraint >25%) ⚠️", visible=True)
add_raster(g01_nfhl, f"{RAST}/nfhl_sfha_exclusion_1km.tif",
           "NFHL SFHA Binary (any overlap = 0.8%)", visible=False)
add_raster(g01_nfhl, f"{RAST}/nfhl_coverage_qa_1km.tif",
           "NFHL Coverage QA — mapped=1 unmapped=0 [F-3: 29.5% unmapped]", visible=False)
add_vector(g01_nfhl, f"{PROC}/nfhl_sfha_7states_EPSG5070.gpkg",
           "nfhl_sfha", "NFHL SFHA Polygons (114,444 features — partial IA/TX/VA)", visible=False)

# NLCD subgroup
g01_nlcd = g01.addGroup("NLCD Land Cover Eligibility")
add_raster(g01_nlcd, f"{RAST}/pct_waterwetland_1km_EPSG5070.tif",
           "NLCD Water/Wetland % (hard excl. if high) ⛔", visible=False)
add_raster(g01_nlcd, f"{RAST}/pct_eligible_1km_EPSG5070.tif",
           "NLCD Eligible Land %", visible=False)

# Slope buildability subgroup
g01_slope = g01.addGroup("Slope / Buildability [Option C: flag only — no hard excl.]")
add_raster(g01_slope, f"{RAST}/slope_pct_below8pct_1km.tif",
           "Slope: % Cell Below 8% (primary buildability metric)", visible=True)
add_raster(g01_slope, f"{RAST}/slope_pct_below3pct_1km.tif",
           "Slope: % Cell Below 3%", visible=False)
add_raster(g01_slope, f"{RAST}/slope_pct_above15pct_1km.tif",
           "Slope: % Cell Above 15% (Appalachian terrain indicator)", visible=False)
add_raster(g01_slope, f"{RAST}/slope_mean_1km_EPSG5070.tif",
           "Slope: Mean Degrees (1km)", visible=False)
add_raster(g01_slope, f"{RAST}/slope_max_1km_EPSG5070.tif",
           "Slope: Max Degrees (1km) — QC/context only", visible=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 02 — ESI — Environmental Stewardship Index
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 02 ESI ---")
g02 = make_group(root, "02 — ESI — Environmental Stewardship Index", visible=False)
add_raster(g02, f"{RAST}/carbon_current_co2e_suitability.tif",
           "Carbon — eGRID2023 CO2e Suitability [scored] ✅", visible=True)
add_raster(g02, f"{RAST}/water_stress_baseline_bws_suitability.tif",
           "Water Stress — Aqueduct Baseline Suitability [scored] ✅", visible=True)
add_raster(g02, f"{RAST}/nri_wildfire_score_1km.tif",
           "NRI Wildfire Risk (county-level regional proxy) [scored] ✅", visible=True)
add_raster(g02, f"{RAST}/nri_inland_flood_score_1km.tif",
           "NRI Inland Flood Risk (gradient outside SFHA) [scored] ✅", visible=True)
add_raster(g02, f"{RAST}/nexgddp_mean_days_gt35_2041_2060.tif",
           "CMIP6 Mean Heat Days >35°C 2041–60 [conditional — supervisor approval req'd]", visible=False)
add_raster(g02, f"{RAST}/carbon_future2040_aer_load_co2e_suit.tif",
           "Carbon — Future 2040 Scenario [sensitivity]", visible=False)
add_raster(g02, f"{RAST}/water_stress_future2050bau_ws_suitability.tif",
           "Water Stress — Future 2050 BAU [sensitivity]", visible=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 03 — OFI — Operational Feasibility Index
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 03 OFI ---")
g03 = make_group(root, "03 — OFI — Operational Feasibility Index", visible=False)
add_raster(g03, f"{RAST}/hifld_tx_230kV_proximity_1km.tif",
           "230kV TX Proximity — SOLE primary grid criterion in OFI [scored] ✅", visible=True)
add_raster(g03, f"{RAST}/tiger_roads_primary_proximity_1km.tif",
           "Road Proximity — Primary S1100 only (mean=42km) [scored] ✅", visible=True)
add_raster(g03, f"{RAST}/tiger_roads_prisec_proximity_1km.tif",
           "Road Proximity — Primary+Secondary S1100+S1200 (mean=7km) [sensitivity]", visible=False)
add_raster(g03, f"{RAST}/hifld_substations_IN_SERVICE_proximity_1km.tif",
           "Substation Proximity [OFI sensitivity — correlated 0.7 with 230kV] ⚠️", visible=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 04 — Grid Readiness Screen (GRS)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 04 GRS ---")
g04 = make_group(root, "04 — Grid Readiness Screen (GRS)", visible=False)
add_raster(g04, f"{RAST}/hifld_tx_345kV_proximity_1km.tif",
           "345kV TX Proximity — GRS Tier 1 primary [NOT independently scored in OFI]", visible=True)
add_raster(g04, f"{RAST}/hifld_tx_230kV_proximity_1km.tif",
           "230kV TX Proximity — GRS Tier 1 secondary", visible=False)
add_raster(g04, f"{RAST}/hifld_substations_IN_SERVICE_proximity_1km.tif",
           "Substation Proximity — GRS Tier 1 tertiary [HIFLD provisional F-6]", visible=False)
add_raster(g04, f"{RAST}/saidi_option_a_custweighted_suitability.tif",
           "SAIDI Customer-Weighted — GRS Tier 2 context [28.5% ND — F-4]", visible=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 05 — Community & Equity Screen
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 05 Community & Equity ---")
g05 = make_group(root, "05 — Community & Equity Screen", visible=False)
add_raster(g05, f"{RAST}/eji_2024_score_1km.tif",
           "EJI 2022 Overall Score (census-tract) [FLAG only — not scored] ✅", visible=True)
add_raster(g05, f"{RAST}/eji_2024_flag_p75_1km.tif",
           "EJI 2022 High-Concern Flag P75 (within-7-state) [24.9% flagged]", visible=True)
add_raster(g05, f"{RAST}/eji_2024_envburd_1km.tif",
           "EJI 2022 Environmental Burden Module", visible=False)
add_raster(g05, f"{RAST}/eji_2024_socvuln_1km.tif",
           "EJI 2022 Social Vulnerability Module", visible=False)
add_vector(g05, f"{PROC}/eji_2024_7states_EPSG5070.gpkg",
           "eji_2022_7states", "EJI 2022 Census Tracts (13,938 features)", visible=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 06 — Risk & Resilience / Uncertainty
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 06 Risk & Resilience ---")
g06 = make_group(root, "06 — Risk & Resilience / Uncertainty Overlay", visible=False)
add_raster(g06, f"{RAST}/nexgddp_std_days_gt35_2041_2060.tif",
           "CMIP6 Inter-model Std Dev Heat Days >35°C 2041–60 [uncertainty overlay M4]", visible=True)
add_raster(g06, f"{RAST}/nri_inland_flood_score_1km.tif",
           "NRI Inland Flood (risk gradient — unmapped NFHL areas)", visible=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 07 — Opportunity Overlay
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 07 Opportunity Overlay ---")
g07 = make_group(root, "07 — Opportunity Overlay (not scored)", visible=False)
add_raster(g07, f"{RAST}/pct_developed_1km_EPSG5070.tif",
           "NLCD % Developed Land (brownfield proxy — not scored)", visible=True)
eia_path = f"{PROC}/eia860_powerplants_operating_7state_EPSG5070.gpkg"
add_vector(g07, eia_path, "eia860_powerplants",
           "EIA-860 2024 Operating Power Plants (3,189 plants — grid context)", visible=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 08 — Validation (NOT scored)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 08 Validation ---")
g08 = make_group(root, "08 — Validation (NOT scored)", visible=True)
add_vector(g08, f"{VAL}/observed_data_center_points/data_centers_7state_EPSG5070.gpkg",
           "data_centers", "Observed Data Centre Locations (1,575 pts — VALIDATION ONLY)", visible=True)
add_vector(g08, f"{VAL}/constrained_random_points/random_eligible_5000_EPSG5070.gpkg",
           "random_eligible", "Constrained Random Eligible Points (5,000 pts)", visible=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 09 — Sensitivity / SAIDI Context
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 09 Sensitivity / SAIDI ---")
g09 = make_group(root, "09 — Sensitivity / SAIDI Context (NOT primary criterion)", visible=False)
add_raster(g09, f"{RAST}/saidi_with_med_1km.tif",
           "SAIDI with MED [sensitivity only — 28.5% ND]", visible=False)
add_raster(g09, f"{RAST}/saidi_without_med_1km.tif",
           "SAIDI without MED [sensitivity only]", visible=False)
add_raster(g09, f"{RAST}/saidi_option_a_custweighted_suitability.tif",
           "SAIDI Option A Customer-Weighted Suitability [structural ND gap F-4]", visible=False)

# ═══════════════════════════════════════════════════════════════════════════════
# 10 — Legacy / Superseded
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 10 Legacy / Superseded ---")
g10 = make_group(root, "10 — Legacy / Superseded", visible=False)
add_raster(g10, f"{RAST}/nri_coastal_flood_score_1km.tif",
           "NRI Coastal Flood [EXCLUDED — 91.75% NoData]", visible=False)

# ── Save ──────────────────────────────────────────────────────────────────────
print(f"\n--- Saving project ---")
project.setFileName(OUT)
ok = project.write()
print(f"  write() returned: {ok}")

if ok and os.path.exists(OUT):
    sz = os.path.getsize(OUT) / 1024
    print(f"  ✅ Saved: {OUT}")
    print(f"     Size: {sz:.1f} KB")
else:
    print(f"  ❌ FAILED to save: {OUT}")

# Layer count
n_layers = len(project.mapLayers())
print(f"  Total layers in project: {n_layers}")

app.exitQgis()
print("\n=== QGIS project build complete ===")
