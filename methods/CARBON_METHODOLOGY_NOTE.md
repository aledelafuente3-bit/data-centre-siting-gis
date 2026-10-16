# Carbon Intensity Criteria — Methodology Note
**Date:** 2026-06-04  
**Status:** QC complete — awaiting supervisor weight decision before MCDA composite

---

## 1. Current Carbon Intensity (eGRID2023 Revision 2)

### 1.1 Source

**EPA eGRID2023 Revision 2**  
File: `egrid2023_data_rev2.xlsx`, sheet `BA23`, 70 balancing authority records  
Downloaded: 2026-06-02 from https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx  
Raw file preserved untouched at: `03_carbon_intensity/raw/egrid2023_rev2/egrid2023_data_rev2.xlsx`

### 1.2 Fields: BACO2RTA vs BAC2ERTA

| Field | Full name | Units | What it measures |
|-------|-----------|-------|-----------------|
| `BACO2RTA` | BA annual CO2 total output emission rate | lb/MWh | CO2 only (combustion emissions) |
| `BAC2ERTA` | BA annual CO2 equivalent total output emission rate | lb/MWh | CO2 + CH4 + N2O (all greenhouse gases, CO2e) |

**Conversion to g/kWh:** 1 lb/MWh × 453.592 g/lb ÷ 1000 kWh/MWh = lb/MWh × 0.453592 g/kWh

**Output rate definition:** Both fields use the *total output* rate — total BA emissions (from generation within the BA) divided by net generation (MWh). This reflects the historical emission intensity of electricity produced, not consumed. It does not include transmission losses or imports.

### 1.3 CO2 vs CO2e Comparison (Study Area)

| Metric | Min | p5 | p25 | p50 | p75 | p95 | Max | Mean | Coverage |
|--------|----:|---:|----:|----:|----:|----:|----:|-----:|---------|
| CO2 (BACO2RTA) | 96.4 | 102.1 | 218.1 | 332.9 | 395.3 | 445.4 | 859.2 | 317.7 | 99.7% |
| CO2e (BAC2ERTA) | 96.9 | 102.2 | 218.6 | 334.2 | 397.5 | 447.9 | 865.5 | 319.1 | 99.7% |

**Pixel-level correlation (1,690,512 valid cells):**
- Pearson r = 0.999989
- Spearman rank correlation r = 0.999987

**Per-BA difference (CO2e − CO2, g/kWh):** Range +0.1 to +6.3 g/kWh (0.1% to 1.3% relative). The CH4 and N2O contribution is small but non-zero for gas- and coal-heavy BAs (LGEE +6.3, TEPC +5.4, WACM +5.8).

**Conclusion:** CO2e and CO2 produce near-identical spatial patterns and rankings across the study area. The spatial ranking difference is negligible (rank r = 0.9999). However, CO2e is the scientifically correct metric for full greenhouse gas accounting.

### 1.4 Primary Metric Recommendation

**Use `BAC2ERTA` (CO2e, g/kWh) as the primary current-carbon criterion.**

Rationale:
1. CO2e is the standard GHG metric used in climate policy and carbon accounting frameworks.
2. The Cambium future-carbon layer (`aer_load_co2e`) is also expressed in CO2e — using CO2e for the current layer improves conceptual consistency with the future layer.
3. Spatial rankings are identical to CO2 at study-area resolution (rank r = 0.9999).
4. The CO2 raster (`BACO2RTA`) is retained as a supporting output for cross-checking.

### 1.5 Join Crosswalk (HIFLD BA Polygon NAME → eGRID BACODE)

The HIFLD BA polygon `NAME` field contains BA codes for 12 entries (direct match) and full organisation names for 21 entries (requiring crosswalk).

**Direct code matches (NAME = BACODE):** AZPS, BPAT, DEAA, ERCO, MISO, PACW, PGE, PJM, SRP, AVA, WALC, SWPP

**Name → BACODE crosswalk:**

| HIFLD NAME | eGRID BACODE | Match type |
|------------|:------------:|-----------|
| HGBA | HGMA | Nickname match (company DBA) |
| ASSOCIATED ELECTRIC COOPERATIVE, INC. | AECI | Full name |
| CALIFORNIA INDEPENDENT SYSTEM OPERATOR | CISO | Full name |
| DUKE ENERGY CAROLINAS | DUK | Full name |
| EL PASO ELECTRIC COMPANY | EPE | Full name |
| IDAHO POWER COMPANY | IPCO | Full name |
| IMPERIAL IRRIGATION DISTRICT | IID | Full name |
| LOUISVILLE GAS AND ELECTRIC COMPANY AND KENTUCKY UTILITIES | LGEE | Full name |
| NEVADA POWER COMPANY | NEVP | Full name |
| PACIFICORP - EAST | PACE | Full name |
| AVANGRID RENEWABLES LLC | AVRN | Full name |
| PUBLIC SERVICE COMPANY OF NEW MEXICO | PNM | Full name |
| TENNESSEE VALLEY AUTHORITY | TVA | Full name |
| TUCSON ELECTRIC POWER COMPANY | TEPC | Full name |
| WESTERN AREA POWER ADMINISTRATION - ROCKY MOUNTAIN REGION | WACM | Full name |
| GRIFFITH ENERGY, LLC | GRIF | Full name |
| GRIDFORCE SOUTH | GRIS | Full name |
| ARLINGTON VALLEY, LLC - AVBA | DEAA | Duplicate polygon same BA |
| GRIDFORCE ENERGY MANAGEMENT, LLC | GRID | Full name |

### 1.6 Unmatched Polygons

Three HIFLD BA polygons could not be assigned an eGRID CO2e value:

| HIFLD NAME | Reason | Mask cells | Area (km²) |
|------------|--------|:----------:|:----------:|
| ELECTRIC ENERGY, INC. | Not in eGRID2023 (small IL BA below 831 MW survey threshold) | 631 | 631 |
| GILA RIVER POWER, LLC | Not in eGRID2023 (small AZ power plant, no BA-level entry) | 4,348 | 4,348 |
| GRIDFORCE SOUTH (GRIS) | In eGRID2023 but CO2 and CO2e both NULL (no generation reported) | 0 | 0 |

**Total NoData from unmatched BAs:** 4,979 km² (0.29% of 7-state mask)  
**Total NoData from all causes:** 4,897 cells (0.29% of 7-state mask) — includes cells at polygon edges

**Note on GILA RIVER POWER:** 4,348 km² is a small AZ area in the western Maricopa/Pinal County region. This NoData zone is within the WALC (Western Area Power) service territory and would receive WALC's CO2e value (218.6 g/kWh) if the HIFLD polygon boundary is slightly misaligned. The supervisor may wish to verify this manually in QGIS.

### 1.7 Rasters Produced

| File | Field | Coverage | Key stats (g/kWh CO2e) |
|------|-------|---------|----------------------|
| `carbon_current_co2_raw.tif` | BACO2RTA | 99.7% | p50=332.9, range 96–859 |
| `carbon_current_co2_suitability.tif` | BACO2RTA | 99.7% | Formula B, p5=102.1, p95=445.4 |
| `carbon_current_co2e_raw.tif` | **BAC2ERTA** (**primary**) | 99.7% | p50=334.2, range 97–866 |
| `carbon_current_co2e_suitability.tif` | **BAC2ERTA** (**primary**) | 99.7% | Formula B, p5=102.2, p95=447.9 |

---

## 2. Future Carbon Intensity (Cambium)

### 2.1 Source and Metric

**Cambium 2022, MidCase scenario** (on disk)  
File: `Cambium22_MidCase_annual_balancingArea.zip`  
Metric: `aer_load_co2e` — Average Emissions Rate per unit of end-use load, CO2-equivalent (kg/MWh = g/kWh)  
Year: 2040  
Spatial resolution: GEA-level (Grid Emissions Area, 18 regions CONUS; 10 GEA regions in the study area)

**`aer_load_co2e` definition:** Modeled CO2e emissions attributed to end-use electricity consumption per MWh of delivered load. Includes combustion emissions + precombustion (upstream) emissions + an allocation for transmission losses and net import/export. This is a *marginal / attributed* load metric, not a historical output rate.

### 2.2 Current-versus-Future Comparability Caveat

**The eGRID current layer and the Cambium future layer are measured on different accounting bases:**

| | eGRID (current) | Cambium (future) |
|-|-----------------|-----------------|
| Type | Historical measurement | Modeled projection |
| Base year | 2023 (reported 2025) | 2040 (projection) |
| Metric | Output emission rate (generation ÷ emissions) | End-use load emission rate (load ÷ attributed emissions) |
| Includes TX losses | No (output at generator) | Yes (delivery to load) |
| Includes CH4 precombustion | Partially (combustion CH4 only) | Yes (full supply-chain) |
| Units | g CO2e/kWh delivered to bus | g CO2e/kWh consumed by end-use |
| Coverage | BA-level (historical registry) | GEA-level (modeled planning region) |

**These are useful complementary criteria but are not a like-for-like time series.** They should not be subtracted to compute a "change" raster. A difference raster would confound the accounting-base change with the actual projected decarbonisation.

### 2.3 Treatment Recommendation

**Recommended approach: Option B — eGRID as primary present-day criterion; Cambium as a separately normalised sensitivity scenario.**

Rationale:
- The accounting bases differ in ways that affect interpretation (output vs load, historical vs modelled, BA vs GEA resolution).
- Treating them as equivalent primary criteria would imply a comparable measurement scale that does not exist.
- The eGRID layer has better spatial resolution (BA-level) and is a verified historical measurement suitable for a primary scored criterion.
- The Cambium 2040 layer adds a forward-looking signal useful for distinguishing regions with high vs low projected decarbonisation rates — appropriate as a sensitivity/secondary criterion.
- Both layers are separately normalised using Formula B, making them individually interpretable on the 0–1 suitability scale.
- The dissertation methodology chapter should explicitly state the accounting-base difference.

### 2.4 Cambium 2024 Feasibility Check

**Status: NOT ACCESSED — network unavailable from processing environment**

What was attempted:
- Direct HTTP requests to `data.nrel.gov/submissions/289` returned no content (network timeout / connection error, exit code 6)
- URL pattern tests for Cambium 2024 GEA CSV files returned HTTP 000 (no connection)

**What is known from prior research (search conducted 2026-06-02):**
- Cambium 2024 workbooks (April 2025 release) are listed at `https://data.nrel.gov/submissions/289`
- The workbooks provide GEA-level subset data for cost and emissions metrics
- Full BA-level data requires the NREL Scenario Viewer (cambium.nrel.gov), not bulk downloadable
- It was not confirmed that `aer_load_co2e` specifically appears in the downloadable workbooks (the workbooks focus on levelised cost and a subset of emission metrics)

**Key differences between Cambium 2022 and Cambium 2024 (from published documentation):**

| Aspect | Cambium 2022 | Cambium 2024 |
|--------|-------------|-------------|
| Release date | Jan 2023 | Apr 2025 |
| IRA implementation | Pre-IRA assumptions (IRA signed Aug 2022, not fully modelled) | Post-IRA, reflects production tax credit extensions and clean energy provisions |
| Nuclear retirements | Economic + age-based retirements | Age-based retirements only (policy alignment) |
| Renewable costs | 2022 market data | 2024 market data (significant solar/storage cost declines) |
| Load growth | Moderate electrification | Higher electrification trajectory (EVs, heat pumps) |
| CO2e projections | Higher mid-case 2040 intensity | Expected lower 2040 intensity due to faster renewable buildout |

**These are substantive methodological and assumption differences.** Cambium 2024 would be expected to project lower 2040 carbon intensities for most GEA regions than Cambium 2022, due to IRA-driven renewable deployment. Using Cambium 2022 therefore produces a conservative (higher-intensity) future scenario, which may slightly understate the decarbonisation expected by 2040.

**Decision for dissertation:**
- Retain Cambium 2022 as documented fallback
- Label clearly in methodology: "Cambium 2022 MidCase (released January 2023); Cambium 2024 could not be accessed programmatically and requires manual download from the NREL Scenario Viewer"
- Supervisor should download Cambium 2024 GEA workbooks manually if a more current projection is required: https://data.nrel.gov/submissions/289 → select Mid-case → download GEA workbook
- If Cambium 2024 GEA workbook contains `aer_load_co2e` for year 2040, the future carbon raster can be regenerated using the same pipeline

**Historical reference file:** No Cambium 2022 or 2024 historical reference file (for cross-validation against eGRID) was identified in the on-disk data package. The Cambium package provides projections only; eGRID is the authoritative historical source.

### 2.5 Cambium 2022 GEA Values at Year 2040 (aer_load_co2e, g/kWh)

| GEA | Study states covered | aer_load_co2e (g/kWh) | Mean across sub-regions |
|-----|---------------------|:--------------------:|:-----------------------:|
| AZNMc | AZ (dominant) | 78.4 | mean of 7 sub-regions |
| ERCTc | TX (ERCOT) | 34.0 | mean of 7 sub-regions |
| MROWc | IA | 30.7 | mean of 15 sub-regions |
| NWPPc | OR, (ID, NV) | 43.8 | mean of 19 sub-regions |
| RFCEc | VA (eastern) | 165.2 | mean of 6 sub-regions |
| RFCWc | WV, (KY, OH) | 186.6 | mean of 16 sub-regions |
| SPSOc | TX (SPP South) | 23.9 | mean of 7 sub-regions |
| SRMVc | TN/AR border (TVA) | 83.7 | mean of 5 sub-regions |
| SRMWc | IL | 93.2 | mean of 7 sub-regions |
| SRVCc | VA/NC border (DUK) | 118.3 | mean of 6 sub-regions |

**Rasters produced:**
- `carbon_future2040_aer_load_co2e_raw.tif` — 99.7% coverage, g CO2e/kWh
- `carbon_future2040_aer_load_co2e_suit.tif` — Formula B inverted (p5=23.9, p95=165.2)

---

## 3. MCDA Status

| Layer | Role | Status |
|-------|------|--------|
| `carbon_current_co2e_raw.tif` | **Primary current-carbon criterion** | QC / Candidate — weight pending |
| `carbon_current_co2_raw.tif` | Supporting comparison output | Retained, not in scored composite |
| `carbon_future2040_aer_load_co2e_raw.tif` | **Sensitivity / secondary future-carbon** | QC / Candidate — weight pending |
| Cambium 2024 future raster | Would replace 2022 if data obtained | Not yet produced |

**No MCDA composite has been run. No weights have been assigned.**
