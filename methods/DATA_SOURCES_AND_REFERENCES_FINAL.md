# Appendix: Data Sources and Provenance

**Sustainable Data Centre Siting — 7-State Multi-Criteria Decision Analysis**
*Prepared for supervisor review | 2026-06-18 | Not for external distribution*

---

**Study states:** Arizona (AZ), Illinois (IL), Iowa (IA), Oregon (OR), Texas (TX), Virginia (VA), West Virginia (WV)
**Projection:** EPSG:5070 (NAD83 / Conus Albers)
**Reference grid:** 1 km × 1 km, 4086 × 2597 cells, extent −2,295,000 / 310,000 / 1,791,000 / 2,907,000
**Document version:** 2026-06-18

> **Note on coverage:** All datasets were clipped to, or evaluated within, the 7-state study area. National datasets are used at full national resolution before clipping; state-by-state downloads are identified explicitly.

---

## Contents

1. [Administrative Boundaries](#1-administrative-boundaries)
2. [Protected Areas — PAD-US 4.1](#2-protected-areas--pad-us-41)
3. [Flood Hazard — FEMA NFHL](#3-flood-hazard--fema-nfhl)
4. [Natural Hazard Risk — FEMA NRI](#4-natural-hazard-risk--fema-nri)
5. [Land Cover — NLCD 2024](#5-land-cover--nlcd-2024)
6. [Water Stress — WRI Aqueduct 4.0](#6-water-stress--wri-aqueduct-40)
7. [Grid Carbon Intensity (Current) — EPA eGRID 2023](#7-grid-carbon-intensity-current--epa-egrid-2023)
8. [Grid Carbon Intensity (Future) — NREL Cambium 2022](#8-grid-carbon-intensity-future--nrel-cambium-2022)
9. [Transmission Lines — HIFLD](#9-transmission-lines--hifld)
10. [Electric Substations — HIFLD](#10-electric-substations--hifld)
11. [Road Network — TIGER/Line 2025](#11-road-network--tigerline-2025)
12. [Terrain and Slope — USGS 3DEP](#12-terrain-and-slope--usgs-3dep)
13. [Climate Projections — NASA NEX-GDDP-CMIP6](#13-climate-projections--nasa-nex-gddp-cmip6)
14. [Environmental Justice Index — CDC/ATSDR EJI 2024](#14-environmental-justice-index--cdcatsdr-eji-2024)
15. [Power Plants — EIA-860 2024](#15-power-plants--eia-860-2024)
16. [Balancing Authorities and Service Territories — EIA-861 / HIFLD](#16-balancing-authorities-and-service-territories--eia-861--hifld)
17. [Grid Reliability (SAIDI) — EIA Form 861 2024](#17-grid-reliability-saidi--eia-form-861-2024)
18. [Data Centre Validation Points](#18-data-centre-validation-points)
19. [Derived Layers and Reference Grid](#19-derived-layers-and-reference-grid)

---

## 1. Administrative Boundaries

State and county boundary files from the U.S. Census Bureau's 2025 TIGER/Line series provide the spatial framework for the entire analysis. These boundaries define the 7-state study area, establish the reference frame for map presentation, and serve as the spatial join key for tabular datasets (notably SAIDI reliability scores and NRI county-level risk indices). No substantive analytical limitations are associated with these standard cartographic boundary files.

### 1.1 State Boundaries (7-State Study Area)

| Field | Value |
|-------|-------|
| **Dataset** | TIGER/Line 2025 — State and Equivalent (National) |
| **Provider** | U.S. Census Bureau, Geography Division |
| **Version / Year** | 2025 vintage (released January 2025) |
| **Access method** | Direct download — TIGER FTP server |
| **URL** | `https://www2.census.gov/geo/tiger/TIGER2025/STATE/tl_2025_us_state.zip` |
| **Access date** | 2026 (exact date not recorded in file metadata) |
| **Raw file path** | `01_boundaries/raw/tl_2025_us_state/tl_2025_us_state.shp` |
| **Processed output** | `11_processed_layers/states7_reprojected_EPSG5070.gpkg` |
| **Role in project** | Reference boundary; map frame; 7-state study area definition |
| **Geometry** | Polygon; CRS reprojected from NAD83 geographic (EPSG:4269) to EPSG:5070 |
| **Caveats** | None. Standard Census cartographic boundary. |

**Citation:**
U.S. Census Bureau. (2025). *TIGER/Line Shapefiles 2025 — States and Equivalent*. U.S. Department of Commerce. Retrieved from https://www2.census.gov/geo/tiger/TIGER2025/STATE/

### 1.2 County Boundaries

| Field | Value |
|-------|-------|
| **Dataset** | TIGER/Line 2025 — Counties and Equivalent (National) |
| **Provider** | U.S. Census Bureau, Geography Division |
| **Version / Year** | 2025 vintage |
| **URL** | `https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip` |
| **Raw file path** | `01_boundaries/raw/tl_2025_us_county/tl_2025_us_county.shp` |
| **Processed output** | `11_processed_layers/counties7_EPSG5070.gpkg` |
| **Role in project** | Reference boundary; SAIDI and NRI join key; map context |
| **Caveats** | None. |

**Citation:**
U.S. Census Bureau. (2025). *TIGER/Line Shapefiles 2025 — Counties and Equivalent*. U.S. Department of Commerce. Retrieved from https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/

---

## 2. Protected Areas — PAD-US 4.1

The Protected Areas Database of the United States (PAD-US) provides the authoritative federal classification of land management status across all US jurisdictions. Version 4.1 was selected as the primary hard-exclusion layer because it is the most recent release and includes updated boundaries for all 7 study states. Areas classified GAP Status 1 or 2 are excluded from all candidate cells, as these designations reflect a primary management mandate for biodiversity protection that is incompatible with large-scale infrastructure development. GAP Status 3 areas — managed for multiple uses including resource extraction — are retained as a planning review flag rather than a hard exclusion, reflecting the need for case-by-case permitting assessment. PAD-US 4.0 is retained on the project file system as a legacy context layer only; all model outputs use version 4.1 exclusively.

### 2.1 PAD-US 4.1 State GDB/KMZ Archives

| Field | Value |
|-------|-------|
| **Dataset** | Protected Areas Database of the United States (PAD-US) Version 4.1 |
| **Provider** | U.S. Geological Survey (USGS), Gap Analysis Project (GAP) |
| **Version / Year** | Version 4.1 (released 2024) |
| **Access method** | Manual browser download from USGS ScienceBase |
| **ScienceBase item** | `https://www.sciencebase.gov/catalog/item/6759abcfd34edfeb8710a004` |
| **Files downloaded** | `PADUS4_1_State_{ST}_GDB_KMZ.zip` for ST ∈ {AZ, IA, IL, OR, TX, VA, WV} |
| **Raw file path** | `08_protected_areas_and_land_cover/raw/pad_us/PADUS4_1_State_{ST}_GDB_KMZ.zip` |
| **Processed outputs** | `11_processed_layers/pad_us_41_gap12_EPSG5070.gpkg` (13,740 features); `11_processed_layers/pad_us_41_gap3_EPSG5070.gpkg` (12,628 features); `11_processed_layers/rasters/pad_us_gap12_exclusion_1km.tif` (98,394 cells = 5.80% of study area); `11_processed_layers/rasters/pad_us_gap3_flag_1km.tif` (214,987 cells = 12.68% of study area) |
| **Role in project** | Module 0 — Hard Exclusion (GAP 1+2); Planning Review Flag (GAP 3) |
| **GAP status definitions used** | GAP 1: managed for biodiversity, natural disturbance processes allowed (highest protection); GAP 2: managed for biodiversity, some extractive use permitted; GAP 3: managed for multiple uses including resource extraction (development may require review); GAP 4: no biodiversity mandate (private/other public land) |
| **Processing applied** | Filter GAP_Sts ∈ {'1','2'} → GAP1+2 GPKG and exclusion raster; filter GAP_Sts = '3' → GAP3 GPKG and flag raster; rasterize to 1 km grid using `gdal_rasterize` with reference mask extent |
| **QC checks** | Grand Canyon NP (AZ) ✅ correctly classified GAP1/2; Shenandoah NP (VA) ✅; Crater Lake NP (OR) ✅; Shawnee NF (IL) correctly GAP3 (multi-use NF — not an error); Monongahela NF (WV) correctly GAP3 (adjacent cells verified). QC passed 2026-06-17. |
| **Legacy version** | PAD-US 4.0 state ZIPs also present at `08_protected_areas_and_land_cover/raw/pad_us/PADUS4_0_State_{ST}_GDB.zip`. PAD-US 4.0 vectors retained at `11_processed_layers/pad_us_40_gap12_EPSG5070.gpkg` and `pad_us_40_gap3_EPSG5070.gpkg` as legacy context layers only. **Model uses 4.1 exclusively.** |
| **Caveats** | GAP status reflects federal/state agency management designation, not physical impassability. Some GAP3 lands (e.g., National Forests) may technically permit infrastructure; individual permit analysis is required for any specific parcel. |

**Citation:**
U.S. Geological Survey. (2024). *Protected Areas Database of the United States (PAD-US) 4.1*. U.S. Department of the Interior, Gap Analysis Project. https://www.sciencebase.gov/catalog/item/6759abcfd34edfeb8710a004

---

## 3. Flood Hazard — FEMA NFHL

Flood exposure is one of the most material physical risks for data centre infrastructure, given the sensitivity of electrical and computing equipment to water intrusion and the regulatory constraints governing construction in Special Flood Hazard Areas (SFHAs). The National Flood Hazard Layer is the statutory basis for the US National Flood Insurance Program and represents the most authoritative nationally consistent flood-zone delineation available. It was used here as the primary basis for hard flood exclusion and fractional flood-penalty scoring. An important coverage caveat applies: approximately 29.5% of the study area falls outside FEMA's mapped FIRM coverage, and those areas must not be interpreted as free from flood risk (see Flag F-3 below).

### 3.1 National Flood Hazard Layer (NFHL) — SFHA and Floodway Polygons

| Field | Value |
|-------|-------|
| **Dataset** | National Flood Hazard Layer (NFHL) — Special Flood Hazard Areas (S_FLD_HAZ_AR) |
| **Provider** | Federal Emergency Management Agency (FEMA), Risk MAP Programme |
| **Version / Year** | Downloaded via REST API; data as of download date |
| **Access method** | FEMA NFHL REST API; state-level GeoJSON export (paginated queries) |
| **API base URL** | `https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer` |
| **States downloaded** | AZ, IL, IA (partial), OR, TX (partial), VA (partial), WV |
| **Raw file paths** | `07_hazards/raw/flood/nfhl/nfhl_sfha_{state}_EPSG5070.geojson` (SFHA polygons); `07_hazards/raw/flood/nfhl/nfhl_availability_{state}_EPSG5070.geojson` (FIRM availability footprints) |
| **Processed outputs** | `11_processed_layers/nfhl_sfha_7states_EPSG5070.gpkg` (merged SFHA polygons); `11_processed_layers/nfhl_availability_7states_EPSG5070.gpkg` (mapped area footprints); `11_processed_layers/rasters/nfhl_sfha_exclusion_1km.tif` (binary: 1=any SFHA overlap); `11_processed_layers/rasters/nfhl_sfha_fraction_1km.tif` (fractional 0–1); `11_processed_layers/rasters/nfhl_floodway_fraction_1km.tif` (floodway fractional 0–1); `11_processed_layers/rasters/nfhl_coverage_qa_1km.tif` (1=FIRM mapped, 0=unmapped) |
| **SFHA zones included** | FLD_ZONE ∈ {'A', 'AE', 'AO', 'AH', 'AR', 'A99', 'VE', 'V'} — all regulatory 1% annual chance (100-year) flood zones |
| **Hybrid exclusion treatment (R-8, approved)** | Floodway fraction > 0 → hard exclusion; SFHA fraction ≥ 25% → strict constraint; SFHA fraction < 25% → planning review flag |
| **Coverage** | 70.5% of study area cells mapped by FIRM; 29.5% unmapped (Flag F-3) |

> **Flag F-3 — Partial API Coverage:** Iowa, Texas, and Virginia had incomplete API retrieval during the initial download. Flood-hazard outputs for these states therefore represent a lower-bound estimate of SFHA extent. Cells lacking FIRM coverage should not be interpreted as flood-safe; pre-FIRM areas may carry unquantified flood exposure. This limitation must be disclosed in any policy application of the SFHA outputs. A retry of the affected OID ranges is queued but not yet completed at the time of this document.

> **Note on unmapped areas:** FEMA's NFHL coverage is not nationally exhaustive. Absence of NFHL data (nfhl_coverage_qa = 0) must not be interpreted as an indication that a cell is free from flood risk.

**Citation:**
Federal Emergency Management Agency. (n.d.). *National Flood Hazard Layer (NFHL)*. FEMA GeoPlatform. Retrieved 2026 from https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer

---

## 4. Natural Hazard Risk — FEMA NRI

The FEMA National Risk Index complements the NFHL by providing a continuous, nationally consistent county-level index of natural hazard risk that extends beyond the binary presence or absence of flood-zone designations. For this project, two NRI sub-indices are used: wildfire risk (as a proxy for fire exposure in the western states) and inland flood risk (as a gradient measure extending outside SFHA boundaries). The NRI therefore operates at a regional scale and fills spatial gaps that the parcel-level NFHL mapping cannot address.

**Important correction to score direction (verified 2026-06-18):** FEMA NRI `RISKS` fields record raw hazard risk index scores on a 0–100 scale, where a higher value indicates greater hazard risk. An earlier version of this documentation incorrectly stated these scores were pre-inverted. Following source-data verification against the paired `RISKR` rating fields and known county examples, the error has been corrected (see full correction note in the processed outputs description). All suitability rasters were regenerated on 2026-06-18 using the corrected formula: `suitability = 1 − (raw_score / 100)`, such that a value of 1.0 indicates the lowest observable risk and 0.0 the highest.

### 4.1 National Risk Index (NRI) — County-Level Scores

| Field | Value |
|-------|-------|
| **Dataset** | FEMA National Risk Index (NRI) for Natural Hazards — County Shapefile |
| **Provider** | Federal Emergency Management Agency (FEMA), National Resilience |
| **Version / Year** | December 2025 release (metadata PDF: `NRI_metadata_December2025.pdf`) |
| **Access method** | Direct download from FEMA NRI data portal |
| **URL** | `https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload//NRI_Shapefile_Counties/NRI_Shapefile_Counties.zip` |
| **Raw file path** | `06_natural_hazards/raw/fema_nri/NRI_Shapefile_Counties.zip` (extracted to `NRI_Shapefile_Counties_extracted/`) |
| **Processed outputs** | `11_processed_layers/fema_nri_counties_EPSG5070.gpkg` (county polygons with all NRI fields); `11_processed_layers/rasters/nri_wildfire_score_1km.tif` (wildfire risk score, 0.10–100; **higher = higher risk**); `11_processed_layers/rasters/nri_inland_flood_score_1km.tif` (inland flooding risk score, 0.22–100; **higher = higher risk**); `11_processed_layers/rasters/nri_coastal_flood_score_1km.tif` (coastal flooding risk score — EXCLUDED); `11_processed_layers/rasters/nri_combined_flood_max_1km.tif` (max of inland/coastal risk scores); `11_processed_layers/rasters/nri_wildfire_suitability_1km.tif` (1−raw/100; 0–1; higher = lower risk = better); `11_processed_layers/rasters/nri_inland_flood_suitability_1km.tif` (1−raw/100; 0–1; higher = lower risk = better); `11_processed_layers/rasters/nri_combined_flood_suitability_1km.tif` (1−raw/100; 0–1) |
| **Role in project** | Module 1 ESI — wildfire risk proxy; flood risk gradient (complement to NFHL, operating outside SFHA boundary) |
| **Spatial resolution** | County-level polygon → rasterised to 1 km cell (all 1 km cells within a county receive the county NRI score) |

> **Score direction — verified correction (2026-06-18):** FEMA NRI `RISKS` fields (`WFIR_RISKS`, `IFLD_RISKS`) are raw hazard risk index scores: a higher value indicates higher hazard risk. This was confirmed by cross-referencing the paired `RISKR` rating fields against known county values. For example: Pima County, AZ (`WFIR_RISKS` = 99.65) is rated "Relatively High" wildfire risk; Scott County, IL (`WFIR_RISKS` = 0.10) is rated "Very Low." Harris County, TX (`IFLD_RISKS` = 99.97) is rated "Very High" inland flood risk. An earlier version of this documentation incorrectly stated these scores were pre-inverted; that error has been corrected. The three suitability rasters were regenerated on 2026-06-18 using `suitability = 1 − (raw_score / 100)`. Prior versions have been overwritten.

> **Resolution caveat:** NRI scores are at county resolution. Within-county spatial variation in hazard intensity is not captured. The NRI wildfire score therefore functions as a regional proxy, not a site-specific fire risk measure. If a Wildland Fire Potential (WHP) layer at 270 m resolution is subsequently incorporated, the NRI wildfire score would be demoted to a context-only layer.

> **NRI coastal flood (excluded):** `nri_coastal_flood_score_1km.tif` carries 91.75% NoData within the 7-state study area, as the majority of study states lack coastal exposure. This layer is excluded from all scoring but retained for reference.

**Citation:**
Federal Emergency Management Agency. (2025, December). *National Risk Index Technical Documentation*. U.S. Department of Homeland Security. https://hazards.fema.gov/nri/

---

## 5. Land Cover — NLCD 2024

Land cover is used in this project for two distinct purposes: first, as the basis for hard exclusion of water bodies and wetlands (where permanent inundation or protected wetland status renders land unsuitable for development); and second, as a proxy for brownfield opportunity identification, where already-developed land may offer advantages for permitting and grid connection relative to greenfield sites. The 2024 Annual NLCD is the most current release of this dataset and was selected to ensure consistency with the 2024 temporal reference for other primary data layers.

### 5.1 Annual National Land Cover Database (NLCD) 2024

| Field | Value |
|-------|-------|
| **Dataset** | Annual National Land Cover Database (NLCD) 2024 — Conterminous United States |
| **Provider** | U.S. Geological Survey (USGS), in partnership with Multi-Resolution Land Characteristics (MRLC) Consortium |
| **Version / Year** | Collection 1, Version 1 (CU_C1V1), year 2024 |
| **Access method** | Direct download from MRLC data portal |
| **URL** | `https://www.mrlc.gov/data/` (annual land cover product) |
| **Raw file path** | `08_protected_areas_and_land_cover/raw/land_cover/Annual_NLCD_LndCov_2024_CU_C1V1.zip` |
| **Processed outputs** | `11_processed_layers/rasters/annual_nlcd_2024_1km_mode_EPSG5070.tif` (modal NLCD class per 1 km cell); `11_processed_layers/rasters/pct_waterwetland_1km_EPSG5070.tif` (fraction 0–1 of cell in water/wetland classes); `11_processed_layers/rasters/pct_eligible_1km_EPSG5070.tif` (fraction of cell in land-eligible classes); `11_processed_layers/rasters/pct_developed_1km_EPSG5070.tif` (fraction of cell already developed — brownfield proxy); `11_processed_layers/rasters/mask_7states_1km_EPSG5070.tif` (study area mask) |
| **Role in project** | Module 0 — Hard Exclusion (water/wetland ≥ 50% of cell); eligible land fraction; brownfield opportunity proxy (Module 5) |
| **NLCD classes for water/wetland exclusion** | Classes 11 (Open Water), 90 (Woody Wetlands), 95 (Emergent Herbaceous Wetlands) |
| **Native resolution** | 30 m |
| **Aggregation** | Fraction calculated by counting 30 m pixels of each class within each 1 km cell and dividing by total pixels per cell |

**Citation:**
Dewitz, J., and U.S. Geological Survey. (2024). *National Land Cover Database (NLCD) 2024 Products* [data set]. U.S. Geological Survey. https://doi.org/10.5066/P9KZCM54

---

## 6. Water Stress — WRI Aqueduct 4.0

Water availability is a first-order operational constraint for data centres, which rely on evaporative cooling and humidity management systems that can draw substantial quantities of water. The WRI Aqueduct 4.0 Water Risk Atlas was selected as the primary water-stress layer because it provides the most methodologically rigorous and spatially consistent global water-risk assessment currently available, enabling meaningful comparison across the diverse hydrological conditions of the 7-state study area — from the arid Southwest to the well-watered Pacific Northwest. The dataset includes both a current baseline and a 2050 business-as-usual projection, enabling sensitivity analysis under projected future water scarcity conditions.

### 6.1 WRI Aqueduct 4.0 — Baseline and Future Annual Water Risk

| Field | Value |
|-------|-------|
| **Dataset** | Aqueduct 4.0 — Annual Baseline Water Risk and Future Water Risk (2050) |
| **Provider** | World Resources Institute (WRI), Aqueduct Water Risk Atlas |
| **Version / Year** | Version 4.0, published July 2023 (file date: `y2023m07d05`) |
| **Access method** | Direct download from WRI Aqueduct portal |
| **URL** | `https://www.wri.org/data/aqueduct-water-risk-atlas` |
| **Raw file paths** | `05_water_stress/raw/aqueduct_csv/Aqueduct40_baseline_annual_y2023m07d05.csv` (baseline water risk scores by HydroBasin); `05_water_stress/raw/aqueduct_csv/Aqueduct40_future_annual_y2023m07d05.csv` (future risk projections); `05_water_stress/raw/aqueduct_gdb/` (GeoDatabase with polygon geometry) |
| **Processed outputs** | `11_processed_layers/rasters/water_stress_baseline_bws_score_raw.tif` (baseline water stress score, raw); `11_processed_layers/rasters/water_stress_baseline_bws_suitability.tif` (inverted, normalised 0–1; higher = lower stress = better); `11_processed_layers/rasters/water_stress_future2050bau_ws_score_raw.tif` (2050 BAU scenario raw); `11_processed_layers/rasters/water_stress_future2050bau_ws_suitability.tif` (2050 BAU suitability, inverted) |
| **Role in project** | Module 1 ESI — water stress suitability (baseline = primary scored; 2050 BAU = sensitivity scenario only) |
| **Indicator used** | `bws` — Baseline Water Stress (ratio of total water withdrawals to available renewable surface water supply, averaged over the period of record) |
| **Spatial unit** | HydroBasin Level 6 watersheds (mean area ~10,000 km²); assigned to 1 km cells by spatial join |
| **Coverage** | Full 0.00% NoData within 7-state study area |

> **Resolution caveat:** Aqueduct 4.0 is a watershed-level product. All 1 km cells within the same HydroBasin Level 6 unit receive identical water stress scores. Sub-basin variation in groundwater availability, consumptive use ratios, and seasonal patterns is not captured at the 1 km cell level.

**Citation:**
Kuzma, S., Bierkens, M.F.P., Lakshman, S., Luo, T., Saccoccia, L., Sutanudjaja, E.H., & Van Beek, R. (2023). *Aqueduct 4.0: Updated decision-relevant global water risk indicators* [Technical note]. World Resources Institute. https://doi.org/10.46830/writn.23.00061

---

## 7. Grid Carbon Intensity (Current) — EPA eGRID 2023

The carbon intensity of the electricity supply is a key sustainability criterion for data centre siting, as electricity consumption accounts for the dominant share of operational greenhouse gas emissions for most facilities. EPA eGRID provides the authoritative published source of subregion-level emissions rates for the US power grid. The 2023 data year (Revision 2) is used as the current-conditions baseline. Non-baseload CO2-equivalent rates are applied in preference to average rates because they better approximate the marginal emissions impact of an incremental electricity consumer such as a data centre.

### 7.1 EPA eGRID 2023 — Subregion Emissions Rates

| Field | Value |
|-------|-------|
| **Dataset** | Emissions & Generation Resource Integrated Database (eGRID) 2023 |
| **Provider** | U.S. Environmental Protection Agency (EPA), Clean Air Markets Division |
| **Version / Year** | 2023 data year; Revision 2 (`egrid2023_data_rev2_REAL.xlsx`) |
| **Access method** | Direct download from EPA eGRID data portal |
| **URL** | `https://www.epa.gov/egrid/download-data` |
| **Raw file paths** | `02_power_grid/raw/egrid_subregions/egrid2023_data_rev2_REAL.xlsx` (tabular emissions data); `02_power_grid/raw/egrid_subregions/eGrid2023_subregions_joined.shp` (subregion boundary shapefile joined with emissions attributes) |
| **Processed outputs** | `11_processed_layers/ba_with_co2e_EPSG5070.gpkg` (balancing area polygons with CO2e rates); `11_processed_layers/rasters/carbon_current_co2e_raw.tif` (non-baseload CO2e lb/MWh, raw values); `11_processed_layers/rasters/carbon_current_co2e_suitability.tif` (inverted, normalised 0–1; higher = lower carbon intensity = better); `11_processed_layers/rasters/carbon_current_co2_raw.tif` (CO2 only, for comparison); `11_processed_layers/rasters/carbon_current_co2_suitability.tif` |
| **Role in project** | Module 1 ESI — grid carbon intensity (primary scored criterion) |
| **Emissions rate used** | Non-baseload CO2-equivalent (CO2e) lb/MWh per eGRID subregion — appropriate for marginal dispatch calculations |
| **Spatial unit** | eGRID subregion boundaries; 7-state study area spans approximately 10–12 subregions |
| **Coverage** | 0.29% NoData (3 Balancing Authorities near state border lack eGRID subregion mapping — Flag F-9) |

> **Flag F-9 — BA boundary mismatch:** Three Balancing Authorities near state borders lack a direct eGRID subregion mapping. Cells in these areas (0.29% of study area) carry NoData on the carbon rasters. These are identified in `00_ADMIN/saidi_analysis_results.json`.

> **Static snapshot:** eGRID 2023 reflects the 2023 generation mix. The electricity sector is undergoing rapid decarbonisation; carbon intensity values will differ at the time of any proposed development. The NREL Cambium 2022 future scenario (Section 8) should be consulted alongside eGRID 2023 for any planning horizon extending to 2030 or beyond.

**Citation:**
U.S. Environmental Protection Agency. (2025). *Emissions & Generation Resource Integrated Database (eGRID) 2023* (Revision 2). EPA Clean Air Markets Division. https://www.epa.gov/egrid

---

## 8. Grid Carbon Intensity (Future) — NREL Cambium 2022

To assess how siting recommendations may change under projected future grid conditions, the NREL Cambium 2022 dataset provides modelled long-run marginal emissions rates by balancing area through 2050 under multiple decarbonisation scenarios. The 2040 MidCase scenario is used here as a mid-century sensitivity check on the current-conditions eGRID baseline. This layer is not used as a primary scored criterion; it serves exclusively as a scenario sensitivity input to be consulted where long-horizon planning considerations are relevant.

### 8.1 NREL Cambium 2022 — Future Annual Emissions by Balancing Area

| Field | Value |
|-------|-------|
| **Dataset** | Cambium 2022 — Long-Run Marginal Emissions Rates, Annual Balancing Area Level |
| **Provider** | National Renewable Energy Laboratory (NREL) |
| **Version / Year** | Cambium 2022 (released 2022); used for 2040 scenario |
| **Access method** | Direct download from NREL Cambium data portal |
| **URL** | `https://www.nrel.gov/analysis/cambium.html` |
| **Raw file paths** | `02_power_grid/raw/cambium_scenarios/Cambium22_MidCase_annual_balancingArea.zip` (Mid-cost, mid-demand scenario); `02_power_grid/raw/cambium_scenarios/Cambium22_MidCase95by2050_annual_balancingArea.zip` (Mid-case with 95% clean electricity by 2050) |
| **Processed outputs** | `11_processed_layers/rasters/carbon_future2040_aer_load_co2e_raw.tif` (Cambium22 MidCase 2040 average emissions rate, CO2e lb/MWh); `11_processed_layers/rasters/carbon_future2040_aer_load_co2e_suit.tif` (inverted, normalised 0–1) |
| **Role in project** | Module 1 ESI — future carbon sensitivity scenario only (NOT primary scored criterion) |
| **Metric used** | Average Emissions Rate (AER) for load (`aer_load_co2e_kg_per_MWh`), year 2040, MidCase scenario |
| **Scenarios available** | MidCase (moderate decarbonisation trajectory); MidCase95by2050 (aggressive clean-energy trajectory) |

> **Sensitivity scenario only:** The Cambium 2022 future carbon layer is used exclusively as a sensitivity scenario to explore how results change under projected 2040 grid conditions. It is not a primary criterion in the baseline MCDA.

> **Vintage note:** Cambium 2022 predates the full implementation period of the Inflation Reduction Act. Actual 2040 grid decarbonisation may differ significantly from these projections, likely in the direction of deeper decarbonisation than the MidCase assumes.

**Citation:**
Gagnon, P., Frazier, W., Reber, T., & Cole, W. (2022). *Cambium 2022 Scenario Descriptions and Documentation*. National Renewable Energy Laboratory. NREL/TP-6A40-84916. https://www.nrel.gov/docs/fy23osti/84916.pdf

---

## 9. Transmission Lines — HIFLD

Proximity to high-voltage transmission infrastructure is a principal determinant of grid interconnection feasibility and cost. Lines operating at 230 kV and above are capable of serving the large, continuous power demands of hyperscale and colocation data centres; distance to such lines strongly influences both interconnection study timelines and the capital cost of grid connection. The HIFLD Electric Power Transmission Lines dataset provides the most comprehensive nationally consistent record of in-service transmission infrastructure and was selected on that basis.

### 9.1 HIFLD Electric Power Transmission Lines

| Field | Value |
|-------|-------|
| **Dataset** | Electric Power Transmission Lines (In Service) |
| **Provider** | Homeland Infrastructure Foundation-Level Data (HIFLD), U.S. Department of Homeland Security |
| **Version / Year** | Accessed 2026-05-30; dataset reflects utility-reported operational lines |
| **Access method** | REST API (ArcGIS FeatureServer) — paginated query with resultOffset |
| **REST endpoint** | `https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Power_Transmission_Lines/FeatureServer/0/query` |
| **Features downloaded** | 52,244 transmission line segments (national) |
| **Raw file path** | Downloaded directly to GeoPackage during processing |
| **Processed outputs** | `11_processed_layers/hifld_tx_IN_SERVICE_EPSG5070.gpkg` (all in-service lines); `11_processed_layers/hifld_tx_IN_SERVICE_230kV_EPSG5070.gpkg` (≥230 kV filter); `11_processed_layers/hifld_tx_IN_SERVICE_345kV_EPSG5070.gpkg` (≥345 kV filter); `11_processed_layers/rasters/hifld_tx_230kV_proximity_1km.tif` (Euclidean distance in metres to nearest ≥230 kV line); `11_processed_layers/rasters/hifld_tx_345kV_proximity_1km.tif` (distance to nearest ≥345 kV line); `11_processed_layers/rasters/hifld_tx_IN_SERVICE_proximity_1km.tif` (distance to any in-service line) |
| **Role in project** | 230 kV proximity: Module 2 OFI — **sole primary grid-access scored criterion**. 345 kV proximity: Grid Readiness Screen (GRS) Tier 1 primary. All-lines proximity: context/GRS. |
| **Anti-double-count rule** | 230 kV and 345 kV proximity are highly correlated. Only ONE voltage-tier proximity is used as the primary OFI grid-access criterion (230 kV). 345 kV is reserved for GRS; both are NOT simultaneously scored at full independent weight in the OFI. |
| **Voltage filter applied** | 230 kV and above for high-voltage layers (VOLTAGE field ≥ 230 in kV units) |

> **Flag F-6 — Provisional provenance:** HIFLD transmission line data derives from utility self-reporting and is subject to periodic update. Line segments may lag behind new construction or decommissioning by months to years. This dataset is appropriate for strategic-scale screening but should not be used for site-level engineering verification, where direct utility enquiry is required.

**Citation:**
Homeland Infrastructure Foundation-Level Data (HIFLD). (2026, May 30). *Electric Power Transmission Lines*. U.S. Department of Homeland Security. Retrieved from https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-power-transmission-lines

---

## 10. Electric Substations — HIFLD

Substation proximity provides a secondary indicator of grid access suitability, reflecting the availability of existing step-down infrastructure through which new interconnection points can be established. It is treated as a supporting layer within the Grid Readiness Screen rather than as an independent primary criterion, given its high spatial correlation (~0.7) with transmission line proximity.

**Provenance advisory:** A specific disclosure is required regarding the accessibility of this dataset (see Flag F-6 below).

### 10.1 HIFLD Substations (In Service)

| Field | Value |
|-------|-------|
| **Dataset** | Electric Substations (In Service) |
| **Provider** | Homeland Infrastructure Foundation-Level Data (HIFLD), U.S. Department of Homeland Security |
| **Version / Year** | Accessed 2026-05-30 |
| **Access method** | REST API (ArcGIS FeatureServer) |
| **REST endpoint** | `https://services6.arcgis.com/OO2s4OoyCZkYJ6oE/arcgis/rest/services/Substations/FeatureServer` |
| **Features downloaded** | 77,946 substations (national) |
| **Processed outputs** | `11_processed_layers/hifld_substations_IN_SERVICE_EPSG5070.gpkg` (in-service substations); `11_processed_layers/rasters/hifld_substations_IN_SERVICE_proximity_1km.tif` (Euclidean distance in metres) |
| **Role in project** | Grid Readiness Screen (GRS) Tier 1 tertiary; OFI sensitivity only (NOT independently scored at full weight — correlated ~0.7 with transmission proximity) |

> **Flag F-6 — Provenance Advisory (action required before submission):** The original HIFLD Substations ArcGIS Online item (`ebe3ae7f76954aba97d1b5b7687dde43`) is no longer publicly accessible as of the download date. The data was retrieved from a republished or mirrored item. Before dissertation submission, the exact item ID and URL of the republished source must be identified, its authoritative HIFLD provenance confirmed, and the citation updated accordingly. Examiners and supervisors should be able to verify the citation independently. This discrepancy must be disclosed in the methods section.

**Citation:**
Homeland Infrastructure Foundation-Level Data (HIFLD). (2026, May 30). *Electric Substations*. U.S. Department of Homeland Security. [Note: original item `ebe3ae7f76954aba97d1b5b7687dde43` no longer publicly accessible at time of access; retrieved from republished item — verify URL before submission.]

---

## 11. Road Network — TIGER/Line 2025

Road access is a practical prerequisite for data centre construction and operation: construction logistics depend on routes capable of carrying heavy and oversized loads, while routine operations require reliable access for personnel and equipment. Two road-network configurations are maintained to support sensitivity analysis — primary roads only (interstates and US highways, suitable for heavy construction traffic) and primary plus secondary roads (a denser network more representative of operational access requirements).

### 11.1 Primary Roads (MTFCC S1100)

| Field | Value |
|-------|-------|
| **Dataset** | TIGER/Line 2025 — Primary Roads (National) |
| **Provider** | U.S. Census Bureau, Geography Division |
| **Version / Year** | 2025 vintage |
| **URL** | `https://www2.census.gov/geo/tiger/TIGER2025/PRIMARYROADS/tl_2025_us_primaryroads.zip` |
| **Raw file path** | `01_RAW_DATA/infrastructure/roads/raw/tl_2025_us_primaryroads.zip` (extracted to `tl_2025_us_primaryroads/`) |
| **Processed outputs** | `11_processed_layers/rasters/tiger_roads_primary_proximity_1km.tif` (Euclidean distance in metres to nearest S1100 road) |
| **MTFCC class** | S1100 — Primary Roads: interstates (I-xx), US highways, and major state routes |
| **Role in project** | Module 2 OFI — primary-only road access (sensitivity variant; primary+secondary preferred) |

### 11.2 Primary and Secondary Roads (MTFCC S1100 + S1200)

| Field | Value |
|-------|-------|
| **Dataset** | TIGER/Line 2025 — Primary and Secondary Roads (State files) |
| **Provider** | U.S. Census Bureau, Geography Division |
| **Version / Year** | 2025 vintage |
| **URLs** | `https://www2.census.gov/geo/tiger/TIGER2025/PRISECROADS/tl_2025_{FIPS}_prisecroads.zip` for FIPS ∈ {04, 17, 19, 41, 48, 51, 54} |
| **Raw file paths** | `01_RAW_DATA/infrastructure/roads/raw/tl_2025_{FIPS}_prisecroads.zip` (7 state files) |
| **Processed outputs** | `11_processed_layers/rasters/tiger_roads_prisec_proximity_1km.tif` (distance to nearest S1100 or S1200 road) |
| **MTFCC classes** | S1100 (interstates/US highways) + S1200 (secondary state routes, arterials) |
| **Role in project** | Module 2 OFI — **preferred road access criterion** (denser network more appropriate for industrial/data-centre access) |
| **Summary statistics** | Primary-only: mean proximity 42,067 m, max 224,056 m; Primary+Secondary: mean 7,358 m, max 80,623 m |

> **Network density note:** Primary-only (S1100) proximity is appropriate for assessing heavy construction logistics, as interstates carry oversized loads. Primary-plus-secondary (S1100+S1200) is more appropriate for routine operational access and is the preferred OFI input. Both are retained for sensitivity comparison.

**Citation:**
U.S. Census Bureau. (2025). *TIGER/Line Shapefiles 2025 — Primary Roads and PRISEC Roads*. U.S. Department of Commerce. https://www2.census.gov/geo/tiger/TIGER2025/

---

## 12. Terrain and Slope — USGS 3DEP

Slope is a construction-cost modifier: steeply sloped terrain increases earthworks costs, complicates drainage design, and may require structural reinforcement of building foundations. At 1 km resolution, the relevant question is what proportion of a candidate cell offers buildable terrain, rather than the mean slope across the cell. Three fraction-based outputs are therefore produced, characterising the share of each cell with slope below or above key engineering thresholds.

### 12.1 USGS 3D Elevation Program (3DEP) — 1 Arc-Second DEM

| Field | Value |
|-------|-------|
| **Dataset** | USGS 3DEP 1 arc-second (approximately 30 m) Digital Elevation Model |
| **Provider** | U.S. Geological Survey (USGS), 3D Elevation Program |
| **Version / Year** | Various tile dates (2019–2023 depending on tile); downloaded 2026 |
| **Access method** | USGS The National Map (TNM) tile-by-tile download |
| **URL base** | `https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/` |
| **Raw file paths** | `08_protected_areas_and_land_cover/raw/dem_3dep/USGS_1_n##w###.tif` (individual 1°×1° tiles covering 7-state study area) |
| **Processed outputs** | `11_processed_layers/rasters/slope_pct_below3pct_1km.tif` (fraction of 1 km cell with slope < 3%, i.e., < ~1.72°); `11_processed_layers/rasters/slope_pct_below8pct_1km.tif` (fraction with slope < 8%, i.e., < ~4.57°); `11_processed_layers/rasters/slope_pct_above15pct_1km.tif` (fraction with slope > 15%, i.e., > ~8.53°); `11_processed_layers/rasters/slope_mean_1km_EPSG5070.tif` (mean slope in degrees within 1 km cell); `11_processed_layers/rasters/slope_max_1km_EPSG5070.tif` (maximum slope in degrees within cell — QC/context only) |
| **Role in project** | Buildability flag / OFI sensitivity (Option C: no hard exclusion — slope used as penalty and sensitivity layer only) |
| **Processing chain** | 1 arc-second tiles → VRT mosaic → reprojected to EPSG:5070 at **100 m intermediate resolution** (fallback from 30 m due to disk space constraints, documented in `13_scripts/step5b_slope_process.sh`) → `gdaldem slope` in degrees → binary threshold masks at 100 m → `gdalwarp -r average` to 1 km fractional rasters |
| **Distribution summary** | `slope_pct_below8pct_1km`: P25=1.0, Mean=0.797 (most study area is buildable); `slope_pct_above15pct_1km`: P75=0.0, Mean=0.117 (bimodal: flat plains vs. Appalachians) |

> **100 m intermediate resolution:** The originally planned 30 m intermediate resolution was replaced with 100 m due to disk space constraints during processing. This reduces the precision of within-cell slope fraction estimates relative to a full 30 m workflow but does not introduce systematic bias. The processing decision is documented in `13_scripts/step5b_slope_process.sh`. For dissertation purposes, this should be described as a processing pragmatism rather than a data limitation.

> **Slope threshold deferred (Option C approved):** No hard exclusion threshold has been applied to any slope raster. Slope is available as an OFI penalty input and sensitivity layer only. The decision to apply any specific threshold (e.g., exclude cells where less than a given percentage of area has slope below 8%) is deferred pending weighting approval.

**Citation:**
U.S. Geological Survey. (2019–2023). *USGS 3D Elevation Program 1 Arc-Second Digital Elevation Model* [Tiled dataset]. The National Map. https://www.usgs.gov/3d-elevation-program

---

## 13. Climate Projections — NASA NEX-GDDP-CMIP6

Future ambient temperature conditions affect the operational efficiency of data centre cooling systems: facilities in regions with high frequencies of extreme heat days face elevated cooling energy demands, mechanical cooling loads, and risks of thermal exceedance events affecting hardware. The NASA NEX-GDDP-CMIP6 downscaled projections provide spatially detailed temperature outputs across multiple CMIP6 models and emissions scenarios, enabling both a mean-projection surface and an inter-model uncertainty estimate for mid-century heat exposure.

### 13.1 NASA NEX-GDDP-CMIP6 — Daily Maximum Temperature

| Field | Value |
|-------|-------|
| **Dataset** | NASA Earth Exchange Global Daily Downscaled Projections (NEX-GDDP-CMIP6) |
| **Provider** | NASA Ames Research Center, NASA Center for Climate Simulation (NCCS) |
| **Version / Year** | CMIP6 (Coupled Model Intercomparison Project Phase 6); downscaled data downloaded 2026 |
| **Access method** | NASA NCCS THREDDS or AWS (s3://nex-gddp-cmip6) |
| **URL** | `https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6` |
| **Raw file paths** | `07_climate_heat/raw/nexgddp_cmip6/tasmax_day_{model}_ssp245_r1i1p1f1_gn_{year}.nc` for model ∈ {ACCESS-CM2, MPI-ESM1-2-HR, MRI-ESM2-0}, year ∈ {2041, 2050, 2060} |
| **Models used** | ACCESS-CM2 (Australian Community Climate and Earth System Simulator); MPI-ESM1-2-HR (Max Planck Institute Earth System Model — High Resolution); MRI-ESM2-0 (Meteorological Research Institute Earth System Model version 2.0) |
| **Scenario** | SSP2-4.5 (Shared Socioeconomic Pathway 2, 4.5 W/m² radiative forcing — "middle of the road") |
| **Variable** | `tasmax` — daily maximum near-surface air temperature (K, converted to °C) |
| **Time period** | 2041, 2050, 2060 (individual years, not a mean period) |
| **Processed outputs** | `11_processed_layers/rasters/nexgddp_mean_days_gt35_2041_2060.tif` (multi-model mean of days >35°C, averaged 2041+2050+2060); `11_processed_layers/rasters/nexgddp_std_days_gt35_2041_2060.tif` (inter-model standard deviation of days >35°C — uncertainty overlay); `11_processed_layers/rasters/nexgddp_mean_days_gt40_2041_2060.tif` (mean days >40°C — extreme threshold, sensitivity scenario); `11_processed_layers/rasters/nexgddp_std_days_gt40_2041_2060.tif` (inter-model std dev of days >40°C) |
| **Role in project** | Module 1 ESI — conditional inclusion (>35°C layer; risk of SW double-count with carbon/water); Module 4 — inter-model std dev as uncertainty overlay (not scored) |
| **Native resolution** | 0.25° × 0.25° (~25 km); bilinear interpolation to 1 km EPSG:5070 grid |
| **Coverage** | 0.00% NoData within 7-state study area |

> **Conditional inclusion:** The `nexgddp_mean_days_gt35_2041_2060.tif` layer is conditionally included in the ESI pending supervisor approval. The risk of double-counting with the carbon intensity criterion — which correlates with cooling-degree demand in the Southwest — must be assessed. If included, it should be noted explicitly that areas with high heat stress already carry a water-stress penalty through the Aqueduct layer.

> **Three-model ensemble:** The inter-model standard deviation raster reflects genuine uncertainty across the three-model ensemble. It is provided as an uncertainty overlay for map interpretation and is not a suitability score.

**Citation:**
Thrasher, B., Wang, W., Michaelis, A., Melton, F., Lee, T., & Nemani, R. (2022). NASA Global Daily Downscaled Projections, CMIP6. *Scientific Data, 9*, 262. https://doi.org/10.1038/s41597-022-01393-4

---

## 14. Environmental Justice Index — CDC/ATSDR EJI 2024

Environmental justice considerations are integral to responsible infrastructure siting. Data centres, as large electricity consumers with land-intensive footprints, have the potential to interact with communities that already experience disproportionate environmental and socioeconomic burdens. The CDC/ATSDR Environmental Justice Index is used here as a flagging layer to identify census tracts in the top quartile of EJ concern within the study area, so that any candidate sites in high-concern areas can be subject to additional review. Critically, EJI is used exclusively as a flag and not as a traded-off criterion in the MCDA, as treating environmental justice concerns as a tradeable weight would imply they can be offset by operational advantages — a methodologically and ethically inappropriate framing.

**Filename discrepancy note:** The raw downloaded file is named `eji_2022_7states.geojson` but the data it contains is the EJI 2024 release. This naming discrepancy arose during the download and processing workflow. All processed rasters and documentation apply the correct label "EJI 2024." The version year must be confirmed against CDC/ATSDR release notes before dissertation submission (see Item V-1).

### 14.1 Environmental Justice Index (EJI) 2024 — Census-Tract Level

| Field | Value |
|-------|-------|
| **Dataset** | Environmental Justice Index (EJI) 2024 |
| **Provider** | Centers for Disease Control and Prevention (CDC) / Agency for Toxic Substances and Disease Registry (ATSDR) |
| **Version / Year** | EJI 2024 (using 2016–2020 ACS data, 2020 NLCD, and 2020 census tracts) |
| **Access method** | Direct download from CDC/ATSDR EJI portal |
| **URL** | `https://www.atsdr.cdc.gov/placeandhealth/eji/data.html` |
| **Raw file path** | `01_RAW_DATA/social_equity/eji_2024/eji_2022_7states.geojson` (70 MB) |
| **Processed outputs** | `11_processed_layers/eji_2024_7states_EPSG5070.gpkg` (census-tract polygons with all EJI fields); `11_processed_layers/rasters/eji_2024_score_1km.tif` (overall EJI score, 0–1; Min=0, Max=1, Mean=0.531); `11_processed_layers/rasters/eji_2024_flag_p75_1km.tif` (binary flag: 1 = EJI score ≥ within-7-state P75); `11_processed_layers/rasters/eji_2024_envburd_1km.tif` (Environmental Burden module score, 0–1; Mean=0.277); `11_processed_layers/rasters/eji_2024_socvuln_1km.tif` (Social Vulnerability module score, 0–1; Mean=0.605) |
| **Role in project** | Module 3 — Community & Equity flag only (NOT a scored trade-off criterion); high-concern flag at P75 |
| **P75 threshold** | 0.6907 (computed within 7-state study area only, not national percentile) |
| **Flag coverage** | 24.9% of valid study-area cells flagged as high EJ concern |
| **Spatial resolution** | Census-tract level (mean tract ~40 km²); rasterised to 1 km by polygon burn |
| **NoData within mask** | <2% |

> **Within-study-area percentile:** The P75 threshold (0.6907) was calculated within the 7-state study area rather than against the national EJI distribution. Using the national percentile would bias the flag toward states with higher aggregate EJ burden nationally and would misrepresent the relative EJ landscape within the study area.

> **Filename discrepancy:** The raw file `eji_2022_7states.geojson` contains EJI 2024 data. This discrepancy must be disclosed in the methods section and the version confirmed before submission (see Item V-1 in the verification register below).

**Citation:**
Centers for Disease Control and Prevention / Agency for Toxic Substances and Disease Registry. (2024). *Environmental Justice Index (EJI) 2024*. U.S. Department of Health and Human Services. https://www.atsdr.cdc.gov/placeandhealth/eji/

---

## 15. Power Plants — EIA-860 2024

The location and generation capacity of existing power plants within and adjacent to the study area informs two aspects of the analysis: spatial context for grid supply proximity, and identification of potential energy-hub sites where proximity to generation may offer brownfield co-location or grid connection advantages. EIA Form 860 is the statutory annual census of US electric generating units and provides the most complete and authoritative plant-level dataset available.

### 15.1 EIA Form EIA-860 — Annual Electric Generator Report (2024)

| Field | Value |
|-------|-------|
| **Dataset** | Annual Electric Generator Report (EIA Form 860) — 2024 |
| **Provider** | U.S. Energy Information Administration (EIA) |
| **Version / Year** | 2024 survey year (reporting 2024 operations) |
| **Access method** | Direct download from EIA website |
| **URL** | `https://www.eia.gov/electricity/data/eia860/` |
| **Raw file paths** | `02_power_grid/raw/eia860_power_plants/eia8602024/2___Plant_Y2024.xlsx` (plant locations, utility, balancing authority); `02_power_grid/raw/eia860_power_plants/eia8602024/3_1_Generator_Y2024.xlsx` (generator-level capacity, fuel, status) |
| **Processed outputs** | `11_processed_layers/eia860_powerplants_operating_7state_EPSG5070.gpkg` (3,189 operating plants in 7-state area); `02_power_grid/raw/eia860_power_plants/eia8602024/plants_7state_operating_2024.csv` (tabular join) |
| **Filters applied** | Status = 'OP' (operating only); 7 states (AZ, IL, IA, OR, TX, VA, WV) |
| **Key attributes** | plant_code, plant_name, state, ba_code, nameplate_mw_total (aggregated from generator level), primary_fuel, latitude_wgs84, longitude_wgs84 |
| **Role in project** | Module 5 / Module 7 — grid context and opportunity overlay (NOT scored); generation supply proximity, brownfield/energy-hub identification |

**Citation:**
U.S. Energy Information Administration. (2025). *Form EIA-860 Annual Electric Generator Report — 2024*. U.S. Department of Energy. https://www.eia.gov/electricity/data/eia860/

---

## 16. Balancing Authorities and Service Territories — EIA-861 / HIFLD

Balancing authority (BA) boundaries and electric utility service territories provide the spatial framework for assigning carbon intensity values from eGRID to individual 1 km cells and for joining SAIDI reliability data to specific utility service areas. These layers function as spatial join keys rather than as directly scored criteria.

### 16.1 Balancing Authority Areas (Control Areas)

| Field | Value |
|-------|-------|
| **Dataset** | Electric Retail Service Territories and Balancing Authority Boundaries |
| **Provider** | EIA (tabular data from Form 861); HIFLD / derived GeoJSON for polygons |
| **Raw file path** | `02_power_grid/raw/control_areas_ba/control-areas-geojson.geojson` |
| **Processed output** | `11_processed_layers/clipped_ba_to_states__reprojected.gpkg`; `11_processed_layers/ba_with_co2e_EPSG5070.gpkg` (with eGRID carbon rates joined) |
| **Role in project** | Grid context; BA boundary layer for carbon intensity assignment; map annotation |

### 16.2 EIA Utility Service Territories

| Field | Value |
|-------|-------|
| **Dataset** | EIA Utility Service Territories |
| **Raw/processed path** | `11_processed_layers/eia_territories_7state_EPSG5070.gpkg` |
| **Role in project** | SAIDI join spatial key; grid reliability context layer; NOT scored |
| **Note** | Service territory polygons joined with HIFLD and EIA-861 SAIDI data during processing |

**Citation (EIA-861):**
U.S. Energy Information Administration. (2024). *Annual Electric Power Industry Report (EIA Form 861)*. U.S. Department of Energy. https://www.eia.gov/electricity/data/eia861/

---

## 17. Grid Reliability (SAIDI) — EIA Form 861 2024

Grid reliability — measured by the frequency and duration of supply interruptions — is an important operational consideration for data centres, where even brief outages can have significant consequences for service continuity and data integrity. The System Average Interruption Duration Index (SAIDI) is the industry-standard metric for this dimension. However, a structural gap in EIA Form 861 reporting coverage (28.5% of the study area carries no SAIDI value) prevents its use as a primary scored criterion; it is retained as a sensitivity and context layer only. The choice between SAIDI calculated with or without Major Event Days (MED) remains unresolved pending supervisor discussion.

### 17.1 System Average Interruption Duration Index (SAIDI)

| Field | Value |
|-------|-------|
| **Dataset** | Electric Power Industry Reliability Survey — SAIDI/SAIFI by utility |
| **Provider** | U.S. Energy Information Administration (EIA), Form EIA-861 |
| **Version / Year** | 2024 survey (reporting 2023 performance data) |
| **Access method** | Direct download from EIA |
| **URL** | `https://www.eia.gov/electricity/data/eia861/` |
| **Raw file paths** | `04_grid_reliability/raw/f8612024/Reliability_2024.xlsx` (SAIDI/SAIFI by utility, with and without major event days); `04_grid_reliability/raw/table_5_06_a.xlsx` (EIA published summary table 5.06.a); `04_grid_reliability/raw/f8612024/` (full EIA-861 2024 workbook set) |
| **Processed outputs** | `11_processed_layers/rasters/saidi_option_a_custweighted_suitability.tif` (customer-weighted SAIDI, inverted normalised, 0–1); `11_processed_layers/rasters/saidi_with_med_1km.tif` (raw SAIDI including Major Event Days); `11_processed_layers/rasters/saidi_without_med_1km.tif` (raw SAIDI excluding MED — IEEE reliability standard); `11_processed_layers/rasters/saidi_coverage_map_1km.tif` (mapped vs. unmapped utility territories); `11_processed_layers/hifld_eia_saidi_joined_QC.gpkg` (HIFLD service territories joined with SAIDI values) |
| **Role in project** | Sensitivity / context only — NOT a primary scored OFI criterion |
| **Metric** | SAIDI = System Average Interruption Duration Index (total customer-hours of outage per year ÷ total customers served) |
| **MED distinction** | "With MED" = total SAIDI including major weather events and wildfires; "Without MED" = IEEE 2.5 Beta method, excluding major event days. Without-MED is the standard grid-reliability benchmark. |
| **Spatial join method** | SAIDI scores assigned to 1 km cells via HIFLD/EIA utility service territory polygons |

> **Flag F-4 — Structural NoData Gap (28.5%):** Twenty-eight and a half per cent of the study area cells lack a SAIDI value because the relevant utilities either did not report to EIA Form 861 or their service territory polygons do not fully cover the study area. This gap is structural: rural electric co-operatives and municipal utilities are exempt from EIA-861 reporting, and no reliable imputation method exists that would not introduce systematic geographic bias. For this reason, SAIDI is classified as a sensitivity and context layer only, and is excluded from the primary baseline OFI scoring. Any inclusion in a future revised analysis would require explicit acknowledgement of this gap.

> **Flag F-5 — MED treatment unresolved:** Whether to use with-MED or without-MED SAIDI depends on the policy question being addressed. The without-MED approach follows IEEE reliability standards and is more stable year-over-year, but it excludes precisely the extreme weather and wildfire events most relevant to data-centre operational resilience. This decision is deferred pending supervisor discussion.

**Citation:**
U.S. Energy Information Administration. (2024). *Annual Electric Power Industry Report (EIA Form 861) — Reliability Data*. U.S. Department of Energy. https://www.eia.gov/electricity/data/eia861/

---

## 18. Data Centre Validation Points

Validation of the MCDA model requires an independent set of known data centre locations against which to compare model-derived suitability scores. A commercial directory dataset covering 1,575 geocoded facility locations within the 7-state study area was used for this purpose. This dataset is not an input to the model and plays no role in the suitability scoring; it serves exclusively as a holdout comparison set to assess whether the model successfully ranks known facility locations above a random draw of eligible sites. Two significant limitations apply: the dataset's commercial provenance cannot be fully verified from file metadata alone, and two study states (Iowa and West Virginia) are entirely absent from the validation set.

### 18.1 Commercial Data Centre Directory — Geocoded Facility Locations

| Field | Value |
|-------|-------|
| **Dataset** | Commercial data centre facility locations — 7-state subset |
| **Source type** | Commercial data centre directory (consistent with Datacenter Hawk / CBRE DC Intelligence export format) |
| **Provenance status** | Exact source confirmed as commercial directory; dataset name and licence not recoverable from file metadata alone. See `06_VALIDATION/DATA_CENTER_VALIDATION_PROVENANCE.md` for full provenance analysis. |
| **Raw file paths** | `10_data_centers_validation/raw/data_centers_locations.xlsx`; `10_data_centers_validation/raw/All data centers locations.xlsx`; `10_data_centers_validation/raw/geocoded.csv` |
| **Record counts** | 1,598 raw records → 1,575 valid records within 7-state mask after clip and deduplication |
| **Processed outputs** | `06_VALIDATION/observed_data_center_points/data_centers_7state_EPSG5070.gpkg`; `06_VALIDATION/extracted_scores/data_center_scores.csv` (raster scores at each point) |
| **Geocoding method** | Address-based geocoding via external API (geocode_cache.csv confirms API geocoding; coordinates are not GPS-confirmed) |
| **Role in project** | Validation only — NOT a scored input in any MCDA criterion. Used to assess whether model suitability outputs correctly rank known facility locations above random eligible sites. |

> **Source attribution:** This dataset was confirmed via facility naming conventions and operator identification to be a commercial directory export. It must not be cited as OpenStreetMap or any other open-data source. Full provenance evidence is documented at `06_VALIDATION/DATA_CENTER_VALIDATION_PROVENANCE.md`.

> **Geographic coverage bias:** Iowa (0 records) and West Virginia (0 records) are entirely absent from the validation set, reflecting commercial directory coverage limitations rather than a true absence of data centres. Virginia dominates the dataset with 615 records, primarily reflecting the Northern Virginia hyperscale corridor. This geographic imbalance must be acknowledged when interpreting validation statistics.

> **Geocoding accuracy:** Coordinates were derived from address geocoding rather than facility-confirmed GPS measurements. Positional accuracy is typically within ±100 m for well-structured US addresses. At 1 km raster resolution, this level of accuracy is unlikely to affect cell assignment for the majority of records.

| State | Raw records | In-mask |
|-------|-------------|---------|
| VA | 615 | 615 |
| TX | 452 | 450 |
| IL | 256 | 246 |
| AZ | 176 | 171 |
| OR | 94 | 93 |
| IA | 0 | 0 |
| WV | 0 | 0 |
| **Total** | **1,598** | **1,575** |

**Citation:**
[Commercial data centre directory — exact source unverifiable from file metadata. Cite as:] Commercial data centre directory provider (name unverified). (n.d.). *Data centre facility locations — 7-state extract* [dataset]. Retrieved via commercial licence. Geocoded coordinates derived by project team using address geocoding API, 2025–2026.

---

## 19. Derived Layers and Reference Grid

The layers described in this section are produced entirely by the project team from the source datasets documented above. They are not independently sourced and carry no independent citation; their provenance is fully traceable to the documented upstream inputs.

### 19.1 Study Area Reference Grid (Mask)

| Field | Value |
|-------|-------|
| **Dataset** | 7-State Study Area 1 km Mask |
| **Source** | Derived from NLCD 2024 land cover (Section 5) |
| **Derivation** | NLCD 30 m pixels aggregated to 1 km EPSG:5070 grid; cells with ≥1 valid NLCD pixel within the 7-state state boundary polygon = value 1 (valid); all other cells = NoData (255) |
| **Raw file path** | `11_processed_layers/rasters/mask_7states_1km_EPSG5070.tif` |
| **Grid specification** | CRS: EPSG:5070 (NAD83 / Conus Albers); Pixel size: 1000 m × 1000 m; Extent: −2,295,000 / 310,000 / 1,791,000 / 2,907,000; Dimensions: 4086 columns × 2597 rows; Valid cells: 1,695,409 |
| **Role in project** | Reference grid for all raster alignment; NoData mask for summary statistics |

### 19.2 Constrained Random Eligible Points

| Field | Value |
|-------|-------|
| **Dataset** | 5,000 random eligible points — constrained to valid, non-excluded study area cells |
| **Source** | Derived; generated by project team |
| **Derivation** | Random sample of 1 km cells within the study area mask excluding cells where pct_waterwetland > 0.5 OR pct_eligible < 0.1 |
| **Processed output** | `06_VALIDATION/constrained_random_points/random_eligible_5000_EPSG5070.gpkg` |
| **Role in project** | Validation comparison baseline — comparison distribution against observed data centre locations |

### 19.3 NRI Suitability Rasters (Derived from NRI raw scores)

| Field | Value |
|-------|-------|
| **Derivation** | NRI raw score rasters (Section 4) transformed to produce normalised 0–1 suitability values using the corrected formula `suitability = 1 − (raw_score / 100)`, clipped to [0, 1]. Regenerated 2026-06-18 following correction of score direction error. |
| **Outputs** | `nri_wildfire_suitability_1km.tif`; `nri_inland_flood_suitability_1km.tif`; `nri_combined_flood_suitability_1km.tif` |
| **Formula** | `suitability = clip(1.0 − (raw_score / 100.0), 0.0, 1.0)` |
| **Note** | Higher raw RISKS scores indicate greater hazard; the inversion ensures that higher suitability values consistently indicate lower risk across all scored layers. |

---

## Flags Register

| Flag | Description | Layers affected |
|------|-------------|-----------------|
| **F-3** | Partial NFHL API coverage — IA, TX, VA are lower-bound estimates; unmapped areas ≠ flood-safe | `nfhl_sfha_*`, `nfhl_floodway_*`, `nfhl_coverage_qa_1km.tif` |
| **F-4** | SAIDI structural NoData gap — 28.5% of study area cells have no SAIDI value; cannot be imputed without bias | `saidi_option_a_*`, `saidi_with_med_*`, `saidi_without_med_*` |
| **F-5** | SAIDI MED treatment unresolved — decision on with/without Major Event Days deferred to supervisor discussion | `saidi_with_med_*`, `saidi_without_med_*` |
| **F-6** | HIFLD provisional provenance — utility self-reported; may lag construction/decommissioning; substations item inaccessible (see Section 10) | `hifld_tx_*`, `hifld_substations_*` |
| **F-7** | CMIP6 three-model ensemble only — inter-model uncertainty meaningful but limited by sample size | `nexgddp_*` |
| **F-8** | EJI used as flag only (not scored trade-off) — EJI filename discrepancy (`eji_2022_*.geojson` actually contains EJI 2024 data) | `eji_2024_*` |
| **F-9** | eGRID BA boundary mismatch — 3 BAs near state borders lack subregion mapping; 0.29% NoData on carbon rasters | `carbon_current_co2e_*`, `carbon_current_co2_*` |

---

## Summary Table

| # | Dataset | Provider | Year | Raw path (abbreviated) | Processed raster(s) | Model role |
|---|---------|----------|------|------------------------|---------------------|------------|
| 1 | TIGER State/County | US Census | 2025 | `01_boundaries/raw/tl_2025_us_*/` | — (vector) | Reference |
| 2 | PAD-US 4.1 | USGS GAP | 2024 | `08_.../raw/pad_us/PADUS4_1_*` | `pad_us_gap12_excl`, `pad_us_gap3_flag` | M0 Hard Excl. |
| 3 | FEMA NFHL | FEMA | Current | `07_hazards/raw/flood/nfhl/` | `nfhl_sfha_*`, `nfhl_floodway_*`, `nfhl_coverage_qa` | M0 Hard Excl. |
| 4 | FEMA NRI | FEMA | Dec 2025 | `06_natural_hazards/raw/fema_nri/` | `nri_wildfire_*`, `nri_inland_flood_*` | M1 ESI |
| 5 | NLCD 2024 | USGS/MRLC | 2024 | `08_.../raw/land_cover/Annual_NLCD_*` | `pct_waterwetland`, `pct_eligible`, `pct_developed` | M0 Hard Excl. / M5 |
| 6 | WRI Aqueduct 4.0 | WRI | 2023 | `05_water_stress/raw/aqueduct_csv/` | `water_stress_baseline_*`, `water_stress_future*` | M1 ESI |
| 7 | EPA eGRID 2023 | EPA | 2023 | `02_.../egrid_subregions/egrid2023_*` | `carbon_current_co2e_*` | M1 ESI |
| 8 | NREL Cambium 2022 | NREL | 2022 | `02_.../cambium_scenarios/Cambium22_*` | `carbon_future2040_*` | Sensitivity only |
| 9 | HIFLD TX Lines | HIFLD/DHS | 2026-05-30 | REST API | `hifld_tx_230kV_*`, `hifld_tx_345kV_*` | M2 OFI / GRS |
| 10 | HIFLD Substations | HIFLD/DHS | 2026-05-30 | REST API | `hifld_substations_*` | GRS / Sensitivity |
| 11 | TIGER Roads 2025 | US Census | 2025 | `01_RAW_DATA/infrastructure/roads/raw/tl_2025_*` | `tiger_roads_primary_*`, `tiger_roads_prisec_*` | M2 OFI |
| 12 | USGS 3DEP 1″ | USGS | 2019–2023 | `08_.../raw/dem_3dep/USGS_1_*.tif` | `slope_pct_below*`, `slope_mean`, `slope_max` | OFI Sensitivity |
| 13 | NASA NEX-GDDP-CMIP6 | NASA | SSP2-4.5, 2041–2060 | `07_climate_heat/raw/nexgddp_cmip6/` | `nexgddp_mean_*`, `nexgddp_std_*` | M1 ESI (conditional) / M4 |
| 14 | CDC/ATSDR EJI 2024 | CDC/ATSDR | 2024 | `01_RAW_DATA/social_equity/eji_2024/eji_2022_7states.geojson` ⚠️ | `eji_2024_score`, `eji_2024_flag_p75`, `eji_2024_envburd`, `eji_2024_socvuln` | M3 CE Flag |
| 15 | EIA-860 Power Plants | EIA | 2024 | `02_.../eia860_power_plants/eia8602024/` | `eia860_powerplants_*` (vector) | M5 Context |
| 16 | EIA BA Territories | EIA/HIFLD | 2024 | `02_.../control_areas_ba/control-areas-geojson.geojson` | `clipped_ba_*`, `eia_territories_*` (vector) | Grid context |
| 17 | EIA Form 861 SAIDI | EIA | 2024 | `04_grid_reliability/raw/f8612024/Reliability_2024.xlsx` | `saidi_*` | Sensitivity only (F-4) |
| 18 | DC Validation Points | Commercial directory | Unknown | `10_data_centers_validation/raw/geocoded.csv` | `data_centers_7state_EPSG5070.gpkg` | Validation only |
| 19 | Derived / Reference | Project team | 2026 | — | `mask_7states_*`, `nri_*_suitability`, `random_eligible_5000` | Reference / Validation |

---

## Items to Verify Before Dissertation Submission

The following issues require attention before this document or any outputs derived from it are submitted for examination or publication. They do not block interpretation work but must be resolved for the final dissertation text.

| # | Issue | Severity | Action required |
|---|-------|----------|-----------------|
| V-1 | **EJI filename/version discrepancy** | High | Raw file `eji_2022_7states.geojson` is in directory `eji_2024/` and all processed outputs are labelled EJI 2024. Confirm with CDC/ATSDR release notes that this file is indeed the 2024 release (not the 2022 release). Cite the confirmed version. If the file is 2022 data, all EJI rasters and documentation must be relabelled. |
| V-2 | **HIFLD Substations provenance** | High | The original ArcGIS Online item (`ebe3ae7f76954aba97d1b5b7687dde43`) is no longer publicly accessible. The download used a republished/mirrored item. Before submission, identify the exact item ID and URL of the item used, confirm it is an authoritative HIFLD source, and update the citation. Supervisor and examiner must be able to access this citation. |
| V-3 | **NFHL partial coverage (IA, TX, VA)** | Medium | API retrieval for Iowa, Texas, and Virginia was incomplete. All NFHL-derived rasters for these states represent a lower-bound estimate of flood-hazard extent. Quantify the gap (% of cells affected), include this in the methods text, and note that an OID retry was queued but not completed. |
| V-4 | **SAIDI structural NoData gap (28.5%)** | Medium | The SAIDI rasters have 28.5% NoData because many rural and co-operative utilities do not report to EIA Form 861. This gap is structural, not correctable by imputation. The methods section must explicitly note this and justify SAIDI's classification as a sensitivity-only layer. The MED treatment (with vs. without Major Event Days) remains unresolved pending supervisor discussion. |
| V-5 | **NRI direction — corrected 2026-06-18** | Resolved | The original processing treated NRI RISKS scores as pre-inverted (100=best); this was wrong. Verified from source data: higher RISKS = higher hazard = worse. Suitability rasters regenerated with `1 − (raw/100)`. Document in methods as a correction applied during QA. |
| V-6 | **Data centre validation point provenance** | Medium | The exact commercial directory source cannot be confirmed from file metadata. If the dissertation requires a citable, licenced data source for validation, this must be resolved. Options: (a) confirm the original licence; (b) replace with an openly licenced directory (e.g., DCIM, OpenStreetMap, or a peer-reviewed dataset); (c) note the limitation explicitly and rely solely on random-eligible-point comparison as a methodological check rather than ground-truth validation. |
| V-7 | **Cambium 2022 vintage relative to IRA** | Low | Cambium 2022 projections predate the Inflation Reduction Act's full implementation. If the future carbon sensitivity scenario is discussed in the dissertation, note that actual 2040 grid carbon intensity may differ substantially from Cambium 2022 projections. Consider noting availability of Cambium 2023 or Standard Scenarios if an update is feasible. |
| V-8 | **TIGER roads 2025 vs. data centre development year** | Low | Road network data is 2025 vintage. If comparing to historical facility locations, note the network may include roads constructed after some facilities were sited. |
| V-9 | **3DEP slope 100 m intermediate resolution** | Low | Processing used 100 m intermediate resolution (not 30 m as originally planned) due to disk space constraints. Acknowledge in the methods appendix. |
| V-10 | **HIFLD transmission lines snap-date** | Low | HIFLD data accessed 2026-05-30. Transmission infrastructure data may not reflect lines announced, under construction, or recently decommissioned. Note as a limitation for the study's operational period. |

---

## Cross-Reference: Active QGIS Layers vs. Source Documentation

All 77 unique datasources used in `DataCenter_Suitability_LAYER_READY_INTERPRETATION.qgz` (84 layers total, some sharing datasources) are documented in this register. The mapping is:

- **DS-01** → `states7_reprojected_EPSG5070.gpkg`, `counties7_EPSG5070.gpkg`
- **DS-02** → `pad_us_41_gap12_EPSG5070.gpkg`, `pad_us_41_gap3_EPSG5070.gpkg`, `pad_us_40_gap1*` (legacy), `pad_us_gap12_exclusion_1km.tif`, `pad_us_gap3_flag_1km.tif`
- **DS-03** → `nfhl_sfha_7states_EPSG5070.gpkg`, `nfhl_availability_*`, all four NFHL rasters
- **DS-04** → `fema_nri_counties_EPSG5070.gpkg`, all `nri_*_score_*` and `nri_combined_flood_max_*` rasters
- **DS-05** → `pct_waterwetland_*`, `pct_eligible_*`, `pct_developed_*`, `annual_nlcd_*`, `mask_7states_*`
- **DS-06** → `water_stress_baseline_*`, `water_stress_future*`
- **DS-07** → `carbon_current_co2e_*`, `carbon_current_co2_*`, `ba_with_co2e_EPSG5070.gpkg`, `clipped_ba_to_states__reprojected.gpkg`
- **DS-08** → `carbon_future2040_aer_load_co2e_suit.tif`
- **DS-09** → `hifld_tx_IN_SERVICE_*.gpkg`, `hifld_tx_230kV_proximity_*`, `hifld_tx_345kV_proximity_*`
- **DS-10** → `hifld_substations_IN_SERVICE_EPSG5070.gpkg`, `hifld_substations_IN_SERVICE_proximity_*`
- **DS-11** → `tiger_primary_roads_*.gpkg`, `tiger_prisec_roads_*.gpkg`, `tiger_roads_primary_proximity_*`, `tiger_roads_prisec_proximity_*`
- **DS-12** → all `slope_*` rasters
- **DS-13** → all `nexgddp_*` rasters
- **DS-14** → `eji_2024_7states_EPSG5070.gpkg`, `eji_2024_score_*`, `eji_2024_flag_*`, `eji_2024_envburd_*`, `eji_2024_socvuln_*`
- **DS-15** → `eia860_powerplants_operating_7state_EPSG5070.gpkg`, `clipped_powerplants.gpkg` (legacy)
- **DS-16** → `eia_territories_7state_EPSG5070.gpkg`, `clipped_ba_to_states__reprojected.gpkg`
- **DS-17** → `hifld_eia_saidi_joined_QC.gpkg`, all `saidi_*` rasters
- **DS-18** → `data_centers_7state_EPSG5070.gpkg`
- **DS-19** → `mask_7states_*`, `random_eligible_5000_EPSG5070.gpkg`, `nri_*_suitability_*` (derived)

**Result: No undocumented active layers. All 77 unique datasources map to a documented source entry.**

---

*Document prepared 2026-06-18. NRI score-direction error corrected 2026-06-18 following source-data verification; all affected suitability rasters regenerated. All file paths relative to project root: `/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/`. This document is in draft form pending supervisor review and should not be circulated externally.*
