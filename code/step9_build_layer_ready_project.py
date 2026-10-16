#!/usr/bin/env python3
"""
step9_build_layer_ready_project.py
Build a fully symbolised QGIS interpretation project for the
Sustainable Data Centre Siting dissertation.

Output: 12_qgis_projects/working/DataCenter_Suitability_LAYER_READY_INTERPRETATION.qgz

Groups:
  00 — Reference Boundaries
  01 — M0 Hard Exclusions
  02 — ESI Environmental Stewardship
  03 — OFI Operational Feasibility
  04 — Grid Readiness Screen
  05 — Community and Equity
  06 — Risk and Resilience
  07 — Opportunity and Context
  08 — Validation
  09 — Sensitivity Context Only

Rules:
  - EPSG:5070 project CRS (patched in XML after save)
  - No /tmp paths
  - Full symbology applied to all layers
  - Defensive: missing files are skipped with warning
"""

import os, sys, zipfile, shutil, re

# ── QGIS bootstrap ────────────────────────────────────────────────────────────
os.environ["PROJ_LIB"]  = "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj"
os.environ["GDAL_DATA"] = "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"
QGIS_PYTHON = "/Applications/QGIS-LTR.app/Contents/MacOS/lib/python3.9/site-packages"
if QGIS_PYTHON not in sys.path:
    sys.path.insert(0, QGIS_PYTHON)

from qgis.core import (
    QgsApplication, QgsProject, QgsCoordinateReferenceSystem,
    QgsRasterLayer, QgsVectorLayer,
    QgsLayerTreeGroup,
    # Raster symbology
    QgsSingleBandPseudoColorRenderer, QgsColorRampShader,
    QgsPalettedRasterRenderer,
    # Vector symbology
    QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer,
    QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsSingleSymbolRenderer,
    QgsSimpleMarkerSymbolLayer,
    # Raster shader
    QgsRasterShader,
)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QColor

QCoreApplication.setOrganizationName("QGIS")
app = QgsApplication([], False)
app.initQgis()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RAST = f"{BASE}/11_processed_layers/rasters"
PROC = f"{BASE}/11_processed_layers"
VAL  = f"{BASE}/06_VALIDATION"
OUT  = f"{BASE}/12_qgis_projects/working/DataCenter_Suitability_LAYER_READY_INTERPRETATION.qgz"

# ── Project setup ─────────────────────────────────────────────────────────────
project = QgsProject.instance()
project.clear()
crs = QgsCoordinateReferenceSystem("EPSG:5070")
project.setCrs(crs)
project.setTitle("Data Centre Siting — Layer Ready Interpretation (EPSG:5070)")
print(f"  Project CRS: {project.crs().authid()}")

root = project.layerTreeRoot()

# ── Layer counters ─────────────────────────────────────────────────────────────
_added = 0
_skipped = 0

# ═══════════════════════════════════════════════════════════════════════════════
# Symbology helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_pseudocolor(lyr, color_stops, min_val=0.0, max_val=1.0):
    """Apply QgsSingleBandPseudoColorRenderer with given color stops."""
    try:
        shader_func = QgsColorRampShader()
        shader_func.setColorRampType(QgsColorRampShader.Interpolated)
        items = []
        for val, hex_color, label in color_stops:
            items.append(QgsColorRampShader.ColorRampItem(val, QColor(hex_color), label))
        shader_func.setColorRampItemList(items)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(shader_func)
        renderer = QgsSingleBandPseudoColorRenderer(lyr.dataProvider(), 1, shader)
        renderer.setClassificationMin(min_val)
        renderer.setClassificationMax(max_val)
        lyr.setRenderer(renderer)
        lyr.triggerRepaint()
    except Exception as e:
        print(f"    [warn] pseudocolor failed for {lyr.name()}: {e}")


def apply_suitability_rdylgn(lyr):
    """0-1 suitability: Red -> Yellow -> Green."""
    _apply_pseudocolor(lyr, [
        (0.0,  "#d73027", "0 - Low Suitability"),
        (0.25, "#f46d43", "0.25"),
        (0.5,  "#ffffbf", "0.5 - Moderate"),
        (0.75, "#a6d96a", "0.75"),
        (1.0,  "#1a9850", "1 - High Suitability"),
    ], 0.0, 1.0)


def apply_risk_ylrd(lyr, min_val=0.0, max_val=1.0):
    """Risk/hazard: Yellow -> Dark red (higher = worse)."""
    _apply_pseudocolor(lyr, [
        (min_val,                              "#ffffcc", "Low"),
        (min_val + (max_val - min_val) * 0.5,  "#fd8d3c", "Moderate"),
        (max_val,                              "#800026", "High"),
    ], min_val, max_val)


def apply_fraction_blues(lyr):
    """Fraction 0-1: White -> Dark blue."""
    _apply_pseudocolor(lyr, [
        (0.0, "#f7fbff", "0%"),
        (0.5, "#6baed6", "50%"),
        (1.0, "#08306b", "100%"),
    ], 0.0, 1.0)


def apply_paletted_binary(lyr, color_1="#8b0000", label_0="No exclusion", label_1="Excluded"):
    """Binary 0/1 paletted: 0=transparent, 1=color."""
    try:
        classes = [
            QgsPalettedRasterRenderer.Class(0, QColor(0, 0, 0, 0), label_0),
            QgsPalettedRasterRenderer.Class(1, QColor(color_1),     label_1),
        ]
        renderer = QgsPalettedRasterRenderer(lyr.dataProvider(), 1, classes)
        lyr.setRenderer(renderer)
        lyr.triggerRepaint()
    except Exception as e:
        print(f"    [warn] paletted failed for {lyr.name()}: {e}")


def apply_saidi_flag_paletted(lyr):
    """SAIDI coverage flag: 0=orange gap, 1=blue has data."""
    try:
        classes = [
            QgsPalettedRasterRenderer.Class(0, QColor("#ff8c00"), "Gap (no data)"),
            QgsPalettedRasterRenderer.Class(1, QColor("#4393c3"), "Has data"),
        ]
        renderer = QgsPalettedRasterRenderer(lyr.dataProvider(), 1, classes)
        lyr.setRenderer(renderer)
        lyr.triggerRepaint()
    except Exception as e:
        print(f"    [warn] SAIDI paletted failed for {lyr.name()}: {e}")


# Vector symbology helpers

def _vec_renderer_simple_fill(fill_color, stroke_color, stroke_width=0.26, fill_alpha=255):
    """Return a QgsSingleSymbolRenderer with simple fill."""
    sym = QgsFillSymbol()
    lyr_sym = QgsSimpleFillSymbolLayer()
    color_obj = QColor(fill_color)
    color_obj.setAlpha(fill_alpha)
    lyr_sym.setColor(color_obj)
    lyr_sym.setStrokeColor(QColor(stroke_color))
    lyr_sym.setStrokeWidth(stroke_width)
    sym.changeSymbolLayer(0, lyr_sym)
    return QgsSingleSymbolRenderer(sym)


def _vec_renderer_no_fill(stroke_color, stroke_width=0.26):
    """Return a QgsSingleSymbolRenderer with no fill, outline only."""
    sym = QgsFillSymbol()
    lyr_sym = QgsSimpleFillSymbolLayer()
    transparent = QColor(0, 0, 0, 0)
    lyr_sym.setColor(transparent)
    lyr_sym.setFillColor(transparent)
    lyr_sym.setStrokeColor(QColor(stroke_color))
    lyr_sym.setStrokeWidth(stroke_width)
    sym.changeSymbolLayer(0, lyr_sym)
    return QgsSingleSymbolRenderer(sym)


def _vec_renderer_line(color, width=1.0):
    sym = QgsLineSymbol()
    lyr_sym = QgsSimpleLineSymbolLayer()
    lyr_sym.setColor(QColor(color))
    lyr_sym.setWidth(width)
    sym.changeSymbolLayer(0, lyr_sym)
    return QgsSingleSymbolRenderer(sym)


def _vec_renderer_marker(color, size=4.0, shape="circle"):
    sym = QgsMarkerSymbol()
    lyr_sym = QgsSimpleMarkerSymbolLayer()
    lyr_sym.setColor(QColor(color))
    lyr_sym.setSize(size)
    shape_map = {
        "circle":   QgsSimpleMarkerSymbolLayer.Circle,
        "star":     QgsSimpleMarkerSymbolLayer.Star,
        "triangle": QgsSimpleMarkerSymbolLayer.Triangle,
    }
    lyr_sym.setShape(shape_map.get(shape, QgsSimpleMarkerSymbolLayer.Circle))
    sym.changeSymbolLayer(0, lyr_sym)
    return QgsSingleSymbolRenderer(sym)


# ── Layer add helpers ─────────────────────────────────────────────────────────

def add_raster(group, path, name, visible=True, sym_fn=None):
    """Add raster layer to group; skip if file missing."""
    global _added, _skipped
    if not os.path.exists(path):
        print(f"  SKIP (not found): {name}")
        _skipped += 1
        return None
    lyr = QgsRasterLayer(path, name)
    if not lyr.isValid():
        print(f"  INVALID: {name} -- {path}")
        _skipped += 1
        return None
    if sym_fn:
        try:
            sym_fn(lyr)
        except Exception as e:
            print(f"    [warn] symbology error for {name}: {e}")
    project.addMapLayer(lyr, False)
    node = group.addLayer(lyr)
    node.setItemVisibilityChecked(visible)
    print(f"  OK  {name}")
    _added += 1
    return lyr


def add_vector(group, path, layername, display_name, visible=True, sym_fn=None):
    """Add vector layer (GPKG) to group; skip if file missing."""
    global _added, _skipped
    if not os.path.exists(path):
        print(f"  SKIP (not found): {display_name}")
        _skipped += 1
        return None
    uri = f"{path}|layername={layername}" if layername else path
    lyr = QgsVectorLayer(uri, display_name, "ogr")
    if not lyr.isValid():
        # Try without layername qualifier (auto-detect first layer)
        lyr2 = QgsVectorLayer(path, display_name, "ogr")
        if lyr2.isValid():
            lyr = lyr2
        else:
            print(f"  INVALID: {display_name} -- {uri}")
            _skipped += 1
            return None
    if sym_fn:
        try:
            sym_fn(lyr)
        except Exception as e:
            print(f"    [warn] symbology error for {display_name}: {e}")
    project.addMapLayer(lyr, False)
    node = group.addLayer(lyr)
    node.setItemVisibilityChecked(visible)
    print(f"  OK  {display_name}")
    _added += 1
    return lyr


def make_group(parent, name, visible=True):
    g = parent.addGroup(name)
    g.setItemVisibilityChecked(visible)
    return g


# ═══════════════════════════════════════════════════════════════════════════════
# 00 — Reference Boundaries  [VISIBLE]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 00 Reference Boundaries ---")
g00 = make_group(root, "00 -- Reference Boundaries", visible=True)

add_vector(g00,
    f"{PROC}/states7_reprojected_EPSG5070.gpkg",
    "states7_reprojected_EPSG5070", "7-State Boundary",
    visible=True,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_no_fill("#404040", 0.8))
)
add_vector(g00,
    f"{PROC}/counties7_EPSG5070.gpkg",
    "counties7_EPSG5070", "County Boundaries",
    visible=True,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_no_fill("#888888", 0.3))
)
add_raster(g00,
    f"{RAST}/mask_7states_1km_EPSG5070.tif",
    "Study Area 1km Mask",
    visible=True,
    sym_fn=apply_fraction_blues
)

# ═══════════════════════════════════════════════════════════════════════════════
# 01 — M0 Hard Exclusions  [HIDDEN]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 01 M0 Hard Exclusions ---")
g01 = make_group(root, "01 -- M0 Hard Exclusions", visible=False)

# PAD-US subgroup
g01_pad = make_group(g01, "PAD-US Protection", visible=False)
add_raster(g01_pad,
    f"{RAST}/pad_us_gap12_exclusion_1km.tif",
    "PAD-US GAP 1+2 Exclusion",
    visible=True,
    sym_fn=lambda l: apply_paletted_binary(l, "#8b0000", "Not excluded", "GAP 1+2 excluded")
)
add_raster(g01_pad,
    f"{RAST}/pad_us_gap3_flag_1km.tif",
    "PAD-US GAP 3 Planning Review",
    visible=False,
    sym_fn=lambda l: apply_paletted_binary(l, "#ff8c00", "No flag", "GAP 3 review flag")
)
add_vector(g01_pad,
    f"{PROC}/pad_us_41_gap12_EPSG5070.gpkg",
    "pad_us_41_gap12_EPSG5070", "PAD-US 4.1 GAP 1+2 Polygons",
    visible=False,
    sym_fn=lambda l: l.setRenderer(
        _vec_renderer_simple_fill("#d73027", "#8b0000", 0.1, fill_alpha=128)
    )
)
add_vector(g01_pad,
    f"{PROC}/pad_us_41_gap3_EPSG5070.gpkg",
    "pad_us_41_gap3_EPSG5070", "PAD-US 4.1 GAP 3 Polygons",
    visible=False,
    sym_fn=lambda l: l.setRenderer(
        _vec_renderer_simple_fill("#ff8c00", "#cc6600", 0.1, fill_alpha=102)
    )
)

# NFHL subgroup
g01_nfhl = make_group(g01, "NFHL Flood Hazard", visible=False)
add_raster(g01_nfhl,
    f"{RAST}/nfhl_floodway_fraction_1km.tif",
    "NFHL Floodway Fraction",
    visible=True,
    sym_fn=apply_risk_ylrd
)
add_raster(g01_nfhl,
    f"{RAST}/nfhl_sfha_fraction_1km.tif",
    "NFHL SFHA Fraction",
    visible=True,
    sym_fn=apply_risk_ylrd
)
add_raster(g01_nfhl,
    f"{RAST}/nfhl_sfha_exclusion_1km.tif",
    "NFHL SFHA Binary",
    visible=False,
    sym_fn=lambda l: apply_paletted_binary(l, "#8b0000", "Not in SFHA", "SFHA excluded")
)
add_raster(g01_nfhl,
    f"{RAST}/nfhl_coverage_qa_1km.tif",
    "NFHL Coverage QA",
    visible=False,
    sym_fn=apply_fraction_blues
)
add_vector(g01_nfhl,
    f"{PROC}/nfhl_sfha_7states_EPSG5070.gpkg",
    "nfhl_sfha", "NFHL SFHA Polygons",
    visible=False,
    sym_fn=lambda l: l.setRenderer(
        _vec_renderer_simple_fill("#4292c6", "#084594", 0.1, fill_alpha=100)
    )
)

# NLCD subgroup
g01_nlcd = make_group(g01, "NLCD Land Cover", visible=False)
add_raster(g01_nlcd,
    f"{RAST}/pct_waterwetland_1km_EPSG5070.tif",
    "NLCD Water/Wetland %",
    visible=False,
    sym_fn=apply_fraction_blues
)
add_raster(g01_nlcd,
    f"{RAST}/pct_eligible_1km_EPSG5070.tif",
    "NLCD Eligible Land %",
    visible=False,
    sym_fn=apply_fraction_blues
)

# ═══════════════════════════════════════════════════════════════════════════════
# 02 — ESI Environmental Stewardship  [HIDDEN]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 02 ESI Environmental Stewardship ---")
g02 = make_group(root, "02 -- ESI Environmental Stewardship", visible=False)

# Carbon subgroup
g02_carbon = make_group(g02, "Carbon", visible=False)
add_raster(g02_carbon,
    f"{RAST}/carbon_current_co2e_suitability.tif",
    "Carbon CO2e Suitability",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g02_carbon,
    f"{RAST}/carbon_current_co2_suitability.tif",
    "Carbon CO2 Suitability alt",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g02_carbon,
    f"{RAST}/carbon_future2040_aer_load_co2e_suit.tif",
    "Carbon CO2e Future 2040",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)

# Water Stress subgroup
g02_water = make_group(g02, "Water Stress", visible=False)
add_raster(g02_water,
    f"{RAST}/water_stress_baseline_bws_suitability.tif",
    "Water Stress Baseline Suitability",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g02_water,
    f"{RAST}/water_stress_future2050bau_ws_suitability.tif",
    "Water Stress Future 2050 BAU",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)

# Water Scarcity Supplementary subgroup
g02_wscarcity = make_group(g02, "Water Scarcity Supplementary", visible=False)
add_raster(g02_wscarcity,
    f"{RAST}/aqueduct_iav_suitability_1km.tif",
    "Aqueduct IAV Suitability",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g02_wscarcity,
    f"{RAST}/aqueduct_gtd_suitability_1km.tif",
    "Aqueduct GTD Suitability",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g02_wscarcity,
    f"{RAST}/pdsi_mean_suitability_1km.tif",
    "PDSI Drought Suitability 2000-2024",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)

# NRI Wildfire subgroup
g02_wildfire = make_group(g02, "NRI Wildfire", visible=False)
add_raster(g02_wildfire,
    f"{RAST}/nri_wildfire_score_1km.tif",
    "NRI Wildfire Score Raw",
    visible=True,
    sym_fn=apply_risk_ylrd
)

# NRI Inland Flood subgroup
g02_flood = make_group(g02, "NRI Inland Flood", visible=False)
add_raster(g02_flood,
    f"{RAST}/nri_inland_flood_score_1km.tif",
    "NRI Inland Flood Score Raw",
    visible=True,
    sym_fn=apply_risk_ylrd
)

# CMIP6 Heat Days subgroup
g02_cmip6 = make_group(g02, "CMIP6 Heat Days", visible=False)
add_raster(g02_cmip6,
    f"{RAST}/nexgddp_mean_days_gt35_2041_2060.tif",
    "CMIP6 Mean Heat Days 2041-2060",
    visible=False,
    sym_fn=apply_risk_ylrd
)
add_raster(g02_cmip6,
    f"{RAST}/nexgddp_std_days_gt35_2041_2060.tif",
    "CMIP6 Heat Days Std Dev",
    visible=False,
    sym_fn=apply_risk_ylrd
)

# ═══════════════════════════════════════════════════════════════════════════════
# 03 — OFI Operational Feasibility  [HIDDEN]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 03 OFI Operational Feasibility ---")
g03 = make_group(root, "03 -- OFI Operational Feasibility", visible=False)

# Transmission Access subgroup
g03_tx = make_group(g03, "Transmission Access", visible=False)
add_raster(g03_tx,
    f"{RAST}/hifld_tx_230kV_proximity_1km.tif",
    "230kV TX Proximity",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)
add_vector(g03_tx,
    f"{PROC}/hifld_tx_IN_SERVICE_230kV_EPSG5070.gpkg",
    "hifld_tx_IN_SERVICE_230kV_EPSG5070", "230kV TX Lines",
    visible=True,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_line("#cc0000", 1.5))
)
add_vector(g03_tx,
    f"{PROC}/hifld_tx_IN_SERVICE_345kV_EPSG5070.gpkg",
    "hifld_tx_IN_SERVICE_345kV_EPSG5070", "345kV TX Lines",
    visible=False,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_line("#660000", 2.0))
)

# Road Access subgroup
g03_road = make_group(g03, "Road Access", visible=False)
add_raster(g03_road,
    f"{RAST}/tiger_roads_prisec_proximity_1km.tif",
    "Road Proximity Primary+Secondary",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g03_road,
    f"{RAST}/tiger_roads_primary_proximity_1km.tif",
    "Road Proximity Primary Only",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_vector(g03_road,
    f"{PROC}/tiger_primary_roads_7states_EPSG5070.gpkg",
    "tiger_primary_roads_7states_EPSG5070", "Primary Roads",
    visible=False,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_line("#888888", 0.5))
)

# Slope Buildability subgroup
g03_slope = make_group(g03, "Slope Buildability", visible=False)
add_raster(g03_slope,
    f"{RAST}/slope_pct_below8pct_1km.tif",
    "Slope pct below 8%",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g03_slope,
    f"{RAST}/slope_pct_below3pct_1km.tif",
    "Slope pct below 3%",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g03_slope,
    f"{RAST}/slope_pct_above15pct_1km.tif",
    "Slope pct above 15%",
    visible=False,
    sym_fn=apply_risk_ylrd
)
add_raster(g03_slope,
    f"{RAST}/slope_mean_1km_EPSG5070.tif",
    "Slope Mean Degrees",
    visible=False,
    sym_fn=apply_risk_ylrd
)
add_raster(g03_slope,
    f"{RAST}/slope_max_1km_EPSG5070.tif",
    "Slope Max Degrees",
    visible=False,
    sym_fn=apply_risk_ylrd
)

# Grid Economics subgroup
g03_econ = make_group(g03, "Grid Economics", visible=False)
add_raster(g03_econ,
    f"{RAST}/ferc_queue_suitability_1km.tif",
    "FERC Queue Suitability",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g03_econ,
    f"{RAST}/ferc_queue_mw_density_1km.tif",
    "FERC Queued MW Raw",
    visible=False,
    sym_fn=apply_risk_ylrd
)
add_raster(g03_econ,
    f"{RAST}/eia_retail_price_suitability_1km.tif",
    "EIA Retail Price Suitability",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)

# ═══════════════════════════════════════════════════════════════════════════════
# 04 — Grid Readiness Screen  [HIDDEN]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 04 Grid Readiness Screen ---")
g04 = make_group(root, "04 -- Grid Readiness Screen", visible=False)
add_raster(g04,
    f"{RAST}/hifld_tx_345kV_proximity_1km.tif",
    "345kV TX Proximity",
    visible=True,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g04,
    f"{RAST}/hifld_substations_IN_SERVICE_proximity_1km.tif",
    "Substations Proximity",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g04,
    f"{RAST}/saidi_option_a_custweighted_suitability.tif",
    "SAIDI Reliability (context)",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g04,
    f"{RAST}/saidi_nodata_flag_1km.tif",
    "SAIDI Coverage Flag",
    visible=False,
    sym_fn=apply_saidi_flag_paletted
)
add_vector(g04,
    f"{PROC}/hifld_substations_IN_SERVICE_EPSG5070.gpkg",
    "hifld_substations_IN_SERVICE_EPSG5070", "Substations",
    visible=False,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_marker("#ffff00", 4.0, "circle"))
)

# ═══════════════════════════════════════════════════════════════════════════════
# 05 — Community and Equity  [HIDDEN]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 05 Community and Equity ---")
g05 = make_group(root, "05 -- Community and Equity [FLAG ONLY]", visible=False)
add_raster(g05,
    f"{RAST}/eji_2024_score_1km.tif",
    "EJI 2024 Overall Score",
    visible=True,
    sym_fn=apply_risk_ylrd
)
add_raster(g05,
    f"{RAST}/eji_2024_flag_p75_1km.tif",
    "EJI 2024 High-Concern Flag P75",
    visible=True,
    sym_fn=lambda l: apply_paletted_binary(l, "#7b2d8b", "Not flagged", "High concern (P75+)")
)
add_raster(g05,
    f"{RAST}/eji_2024_envburd_1km.tif",
    "EJI 2024 Environmental Burden",
    visible=False,
    sym_fn=apply_risk_ylrd
)
add_raster(g05,
    f"{RAST}/eji_2024_socvuln_1km.tif",
    "EJI 2024 Social Vulnerability",
    visible=False,
    sym_fn=apply_risk_ylrd
)
add_vector(g05,
    f"{PROC}/eji_2024_7states_EPSG5070.gpkg",
    "eji_2024_7states_EPSG5070", "EJI 2024 Census Tracts",
    visible=False,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_no_fill("#888888", 0.15))
)

# ═══════════════════════════════════════════════════════════════════════════════
# 06 — Risk and Resilience  [HIDDEN]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 06 Risk and Resilience ---")
g06 = make_group(root, "06 -- Risk and Resilience", visible=False)
add_raster(g06,
    f"{RAST}/nexgddp_std_days_gt35_2041_2060.tif",
    "CMIP6 Std Dev Heat Days",
    visible=True,
    sym_fn=apply_risk_ylrd
)
add_raster(g06,
    f"{RAST}/nfhl_coverage_qa_1km.tif",
    "NFHL Coverage QA (unmapped areas)",
    visible=False,
    sym_fn=apply_fraction_blues
)

# ═══════════════════════════════════════════════════════════════════════════════
# 07 — Opportunity and Context  [HIDDEN]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 07 Opportunity and Context ---")
g07 = make_group(root, "07 -- Opportunity and Context", visible=False)
add_raster(g07,
    f"{RAST}/pct_developed_1km_EPSG5070.tif",
    "NLCD % Developed Land",
    visible=True,
    sym_fn=apply_fraction_blues
)
add_vector(g07,
    f"{PROC}/eia860_powerplants_operating_7state_EPSG5070.gpkg",
    "eia860_powerplants_operating_7state_EPSG5070", "EIA-860 Power Plants",
    visible=True,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_marker("#1f78b4", 4.0, "triangle"))
)

# ═══════════════════════════════════════════════════════════════════════════════
# 08 — Validation  [VISIBLE]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 08 Validation ---")
g08 = make_group(root, "08 -- Validation", visible=True)
add_vector(g08,
    f"{VAL}/observed_data_center_points/data_centers_7state_EPSG5070.gpkg",
    "data_centers_7state_EPSG5070", "Data Centre Locations",
    visible=True,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_marker("#33a02c", 6.0, "star"))
)
add_vector(g08,
    f"{VAL}/constrained_random_points/random_eligible_5000_EPSG5070.gpkg",
    "random_eligible_5000_EPSG5070", "Random Eligible Points",
    visible=False,
    sym_fn=lambda l: l.setRenderer(_vec_renderer_marker("#888888", 3.0, "circle"))
)

# ═══════════════════════════════════════════════════════════════════════════════
# 09 — Sensitivity Context Only  [HIDDEN]
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- 09 Sensitivity Context Only ---")
g09 = make_group(root, "09 -- Sensitivity Context Only", visible=False)
add_raster(g09,
    f"{RAST}/saidi_option_a_custweighted_suitability.tif",
    "SAIDI Reliability",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g09,
    f"{RAST}/pdsi_mean_suitability_1km.tif",
    "PDSI Drought Suitability",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g09,
    f"{RAST}/water_stress_future2050bau_ws_suitability.tif",
    "Water Stress Future 2050",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)
add_raster(g09,
    f"{RAST}/carbon_future2040_aer_load_co2e_suit.tif",
    "Carbon Future 2040",
    visible=False,
    sym_fn=apply_suitability_rdylgn
)

# ── Save project ──────────────────────────────────────────────────────────────
print(f"\n--- Saving project ---")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
project.setFileName(OUT)
ok = project.write()
print(f"  write() returned: {ok}")

n_layers = len(project.mapLayers())
print(f"  Total layers in project: {n_layers}")
print(f"  Layers added: {_added}")
print(f"  Layers skipped: {_skipped}")

app.exitQgis()

if not (ok and os.path.exists(OUT)):
    print(f"  FAILED to save: {OUT}")
    sys.exit(1)

# ── CRS XML patch ─────────────────────────────────────────────────────────────
print("\n--- Patching CRS in QGZ ---")

CRS_XML = """<spatialrefsys nativeFormat="Wkt">
  <wkt>PROJCRS["NAD83 / Conus Albers",BASEGEOGCRS["NAD83",DATUM["North American Datum 1983",ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4269]],CONVERSION["Conus Albers",METHOD["Albers Equal Area",ID["EPSG",9822]],PARAMETER["Latitude of false origin",23,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8821]],PARAMETER["Longitude of false origin",-96,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8822]],PARAMETER["Latitude of 1st standard parallel",29.5,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8823]],PARAMETER["Latitude of 2nd standard parallel",45.5,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8824]],PARAMETER["Easting at false origin",0,LENGTHUNIT["metre",1],ID["EPSG",8826]],PARAMETER["Northing at false origin",0,LENGTHUNIT["metre",1],ID["EPSG",8827]]],CS[Cartesian,2],AXIS["easting (X)",east,ORDER[1],LENGTHUNIT["metre",1]],AXIS["northing (Y)",north,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Data analysis and small scale data presentation for contiguous lower 48 states."],AREA["United States (CONUS) - Alabama; Arizona; Arkansas; California; Colorado; Connecticut; Delaware; Florida; Georgia; Idaho; Illinois; Indiana; Iowa; Kansas; Kentucky; Louisiana; Maine; Maryland; Massachusetts; Michigan; Minnesota; Mississippi; Missouri; Montana; Nebraska; Nevada; New Hampshire; New Jersey; New Mexico; New York; North Carolina; North Dakota; Ohio; Oklahoma; Oregon; Pennsylvania; Rhode Island; South Carolina; South Dakota; Tennessee; Texas; Utah; Vermont; Virginia; Washington; West Virginia; Wisconsin; Wyoming."],BBOX[24.41,-124.79,49.38,-66.91]],ID["EPSG",5070]]</wkt>
  <proj4>+proj=aea +lat_0=23 +lon_0=-96 +lat_1=29.5 +lat_2=45.5 +x_0=0 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs</proj4>
  <srsid>3401</srsid>
  <srid>5070</srid>
  <authid>EPSG:5070</authid>
  <description>NAD83 / Conus Albers</description>
  <projectionacronym>aea</projectionacronym>
  <ellipsoidacronym>EPSG:7019</ellipsoidacronym>
  <geographicflag>false</geographicflag>
</spatialrefsys>"""

TMP_DIR = OUT + "_crs_patch_tmp"
if os.path.exists(TMP_DIR):
    shutil.rmtree(TMP_DIR)
os.makedirs(TMP_DIR, exist_ok=True)

with zipfile.ZipFile(OUT, 'r') as zin:
    zin.extractall(TMP_DIR)

# Find the .qgs file inside
qgs_file = None
for fname in os.listdir(TMP_DIR):
    if fname.endswith(".qgs"):
        qgs_file = os.path.join(TMP_DIR, fname)
        break

if not qgs_file:
    print("  ERROR: no .qgs file found inside QGZ")
    shutil.rmtree(TMP_DIR)
    sys.exit(1)

with open(qgs_file, 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Patch <projectCrs> block
projectcrs_pattern = re.compile(
    r'<projectCrs>.*?</projectCrs>',
    re.DOTALL
)
new_project_crs = f"<projectCrs>\n{CRS_XML}\n</projectCrs>"

if projectcrs_pattern.search(xml_content):
    xml_patched = projectcrs_pattern.sub(new_project_crs, xml_content, count=1)
    print("  projectCrs block patched.")
else:
    print("  WARNING: <projectCrs> not found -- appending before </qgis>")
    xml_patched = xml_content.replace(
        "</qgis>",
        f"{new_project_crs}\n</qgis>",
        1
    )

# Sanity checks on patched content
problems = []
if "/tmp" in xml_patched:
    problems.append("/tmp path found in XML")
if "pad_us_40" in xml_patched:
    problems.append("pad_us_40 reference found in XML")
if "EJI 2022" in xml_patched:
    problems.append("'EJI 2022' string found -- should be 'EJI 2024'")
for p in problems:
    print(f"  WARNING: {p}")
if not problems:
    print("  Sanity checks: all passed (no /tmp, no pad_us_40, no EJI 2022)")

with open(qgs_file, 'w', encoding='utf-8') as f:
    f.write(xml_patched)

# Repack as QGZ
TMP_OUT = OUT + ".tmp_repack.qgz"
with zipfile.ZipFile(TMP_OUT, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
    for dirpath, dirnames, files in os.walk(TMP_DIR):
        for file in files:
            file_path = os.path.join(dirpath, file)
            arcname = os.path.relpath(file_path, TMP_DIR)
            zout.write(file_path, arcname)

shutil.move(TMP_OUT, OUT)
shutil.rmtree(TMP_DIR)

sz_kb = os.path.getsize(OUT) / 1024
print(f"\n=== QGZ build complete ===")
print(f"  Output : {OUT}")
print(f"  Size   : {sz_kb:.1f} KB")
print(f"  Layers : {n_layers}")
if sz_kb < 100:
    print("  WARNING: file is smaller than 100 KB -- may be incomplete")
else:
    print("  Size check: OK (>100 KB)")
