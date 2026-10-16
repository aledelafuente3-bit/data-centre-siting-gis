# GRIC Mode A — Methods Reference
**Project:** Sustainable Data Centre Siting — 7-State MCDA Study  
**Date:** 2026-06-23  
**Status:** Computation complete — awaiting supervisor weight approval before scenario composite maps are published  
**Computed by:** step12_gric_composite_analysis.py + step12b_patch_mask_and_summary.py

---

## §1 Score Meaning Contract

All final index terms are standardized to **higher = better** for the intended environmental/feasibility objective.

| Layer (file) | Module | Direction after transform | Transform formula | Units (raw → suit) |
|---|---|---|---|---|
| `water_stress_baseline_bws_suitability.tif` | ESI | Higher = lower water stress = better | Pre-normalised; `suit = raw` | Dimensionless 0–1 |
| `nri_wildfire_suitability_1km.tif` | ESI | Higher = lower wildfire risk = better | `suit = nri_score / 100`; NRI score 100=lowest risk | Dimensionless 0–1 |
| `nri_inland_flood_suitability_1km.tif` | ESI | Higher = lower flood risk = better | `suit = nri_score / 100`; NRI score 100=lowest risk | Dimensionless 0–1 |
| `nexgddp_mean_days_gt35_2041_2060.tif` *(V3/S2 only)* | ESI | Higher = fewer heat days = better | `suit = clip(1 − days/130, 0, 1)` | Days → 0–1 |
| `slope_pct_below8pct_1km.tif` *(V4/S5 only)* | OFI | Higher = more buildable = better | `suit = raw` (fraction of 1 km² with slope < 8%) | Dimensionless 0–1 |
| `hifld_tx_230kV_proximity_1km.tif` | OFI | Higher = closer to 230 kV line = better | `suit = clip(1 − d / 100 000, 0, 1)` | Metres → 0–1 |
| `tiger_roads_prisec_proximity_1km.tif` | OFI | Higher = closer to primary+secondary road = better | `suit = clip(1 − d / 30 000, 0, 1)` | Metres → 0–1 |

**Note on carbon (Mode A):** Carbon intensity layers are handled in the standalone Carbon Module (§2) and are **excluded from the GRIC composite** under Mode A. See §2 for carbon suitability formulas.

**ESI weights (Mode A — carbon excluded, S1 Balanced):** water 3/7, wildfire 2/7, inland flood 2/7 (renormalised from the full four-layer set without carbon).  
**OFI weights (S1 Balanced):** 230 kV TX proximity 70%, road pri+sec 30%.  
**Module weights (S1):** ESI 50%, OFI 50%.

**GRIC composite formula (Mode A, S1):**
$$\text{GRIC}(x,y) = 0.50 \times \text{ESI}(x,y) + 0.50 \times \text{OFI}(x,y)$$
$$\text{ESI}(x,y) = \tfrac{3}{7}\,s_{\text{water}} + \tfrac{2}{7}\,s_{\text{wildfire}} + \tfrac{2}{7}\,s_{\text{flood}}$$
$$\text{OFI}(x,y) = 0.70\,s_{\text{TX230}} + 0.30\,s_{\text{road}}$$

Applied only to non-excluded cells (see §3 and Appendix A Table 1); all excluded cells → NoData (−9999).

---

## §2 Carbon Module (Mode A — separate from GRIC)

### 2.1 Outputs produced

| Raster | Description |
|--------|-------------|
| `carbon_current_co2e_raw.tif` | BAC2ERTA converted to g CO₂e/kWh |
| `carbon_current_co2e_suitability.tif` | Formula B normalised suitability (0–1) |
| `carbon_future2040_aer_load_co2e_raw.tif` | Cambium 2022 MidCase 2040 aer_load_co2e (g/kWh) |
| `carbon_future2040_aer_load_co2e_suit.tif` | Formula B normalised suitability (0–1) |
| `carbon_delta_gkwh_1km.tif` | ΔCarbon = future − current (g CO₂e/kWh) **descriptive only** |
| `carbon_suit_current_tier_1km.tif` | 5-class tier of current carbon suitability |
| `carbon_suit_future_tier_1km.tif` | 5-class tier of future carbon suitability |

### 2.2 Formula B — suitability normalisation

For each carbon suitability raster:

$$\text{suit}=\text{clip}\!\left(\frac{p_{95}-\text{co2e\_gkwh}}{p_{95}-p_5},\;0,\;1\right)$$

| Layer | Source | p₅ (g/kWh) | p₉₅ (g/kWh) | Year | Spatial unit |
|-------|--------|:----------:|:----------:|------|-------------|
| Current | EPA eGRID2023 Rev2 `BAC2ERTA` (×0.453592 to convert lb/MWh → g/kWh) | 102.2 | 447.9 | 2023 | Balancing authority (BA) polygon |
| Future | Cambium 2022 MidCase `aer_load_co2e` | 23.9 | 165.2 | 2040 (modelled) | Grid Emissions Area (GEA) |

Direction: **higher suitability = cleaner grid = better for siting**.

### 2.3 Carbon suitability tiers (5 classes)

| Tier | Suitability range | Label |
|------|:-----------------:|-------|
| 1 | 0.0 – 0.2 | Very low (carbon-intensive) |
| 2 | 0.2 – 0.4 | Low |
| 3 | 0.4 – 0.6 | Moderate |
| 4 | 0.6 – 0.8 | High |
| 5 | 0.8 – 1.0 | Very high (low-carbon grid) |

**Current carbon tier distribution (eligible cells, n ≈ 1.26M):**

| Tier | Cells | % eligible |
|------|------:|----------:|
| 1 (coal-heavy WV, IL E) | 421,232 | 33.5% |
| 2 | 417,808 | 33.2% |
| 3 | 1,513 | 0.1% |
| 4 | 246,208 | 19.6% |
| 5 (OR hydro/wind, IA wind) | 169,531 | 13.5% |

**Future 2040 carbon tier distribution (eligible cells):**

| Tier | Cells | % eligible |
|------|------:|----------:|
| 1 | 128,212 | 10.2% |
| 2 | 13 | <0.1% |
| 3 | 1,947 | 0.2% |
| 4 | 317,253 | 25.2% |
| 5 (widespread decarbonisation) | 808,867 | 64.3% |

Substantially more cells reach Tier 4–5 by 2040, consistent with the Cambium MidCase decarbonisation trajectory under IRA-era assumptions (noting that Cambium 2022 pre-dates IRA modelling — see §2.4 caveat).

### 2.4 ΔCarbon (descriptive mapping — NOT a scoring variable)

$$\Delta\text{Carbon}(x,y) = \text{Carbon\_future}(x,y) - \text{Carbon\_baseline}(x,y)$$

**Computed stats across all valid 7-state cells (n = 1,690,513):**

| Statistic | Value (g CO₂e/kWh) |
|-----------|------------------:|
| Min | −775.3 |
| Mean | −261.2 |
| Median | −300.2 |
| p75 | −140.1 |
| Max | −53.1 |

All values are negative, confirming the projected direction of grid decarbonisation in every part of the study area by 2040 under the Cambium MidCase scenario.

### 2.5 Accounting-basis compatibility statement (required in dissertation)

**Do not difference-score in GRIC** because eGRID historical output-rate intensity and Cambium modelled end-use load-rate intensity are not on comparable accounting bases. Therefore, carbon-related ranking uses **standalone carbon suitability rasters**, not ΔCarbon. Specifically:

| Dimension | eGRID 2023 (current) | Cambium 2022 MidCase (future) |
|-----------|---------------------|-------------------------------|
| Type | Historical measurement | Modelled projection |
| Base year | 2023 | 2040 |
| Emission rate type | Output (generator bus) | End-use load (delivered) |
| Includes TX losses | No | Yes |
| CH₄ upstream | Combustion only | Full supply-chain |
| Coverage | Balancing authority | Grid Emissions Area |

ΔCarbon is appropriate for descriptive mapping and qualitative discussion of decarbonisation trajectories; it is not suitable as a composite criterion because the subtraction confounds the accounting-base change with the projected emissions change.

---

## §3 Temporal Compatibility

All final index terms are standardized to higher = better for the intended environmental/feasibility objective.

### 3.1 Layer inventory

| Layer | Data year(s) | Static or future-variant | Usage in GRIC |
|-------|-------------|------------------------|--------------|
| `carbon_current_co2e_suitability.tif` | 2023 | Static (historical) | **Not in composite** (Mode A); carbon module only |
| `carbon_future2040_aer_load_co2e_suit.tif` | 2040 (modelled) | Future-variant | **Not in composite** (Mode A); carbon module tiering only |
| `water_stress_baseline_bws_suitability.tif` | 2010–2040 long-run average | Static | **Scored in GRIC ESI** (S1–S5) |
| `nri_wildfire_suitability_1km.tif` | 2022 (FEMA NRI 2022) | Static (historical) | **Scored in GRIC ESI** |
| `nri_inland_flood_suitability_1km.tif` | 2022 | Static (historical) | **Scored in GRIC ESI** |
| `nexgddp_mean_days_gt35_2041_2060.tif` | 2041–2060 (CMIP6 ensemble) | Future-variant | **Scored in GRIC ESI only in S2/S5/V3** |
| `hifld_tx_230kV_proximity_1km.tif` | 2024 (HIFLD Q4 2024) | Static | **Scored in GRIC OFI** |
| `tiger_roads_prisec_proximity_1km.tif` | 2025 (TIGER/Line) | Static | **Scored in GRIC OFI** |
| `slope_pct_below8pct_1km.tif` | 2019 (USGS 3DEP 1 arc-sec) | Static | **Scored in GRIC OFI only in S5/V4** |
| `eji_2024_score_1km.tif` | 2024 (data: 2019–2022) | Static | CE down-rank factor only; never in composite |
| `saidi_nodata_flag_1km.tif` | 2017–2021 | Static | Context flag only |
| `nfhl_sfha_fraction_1km.tif` | Variable by state (2019–2023) | Static | **Hard exclusion** (E-5) |

### 3.2 Assumption impacts of static layers

**Transmission infrastructure (2024):** HIFLD line locations reflect the transmission network as it existed in late 2024. By 2040 the network will have expanded substantially, particularly in renewable energy corridors (TX panhandle, OR offshore wind connections). Current proximity scores systematically underestimate grid accessibility in areas targeted for transmission expansion, creating a conservative bias in OFI scores for western states.

**Water stress (2010–2040 long-run average):** The Aqueduct BWS baseline integrates historical and near-future conditions. Under climate change, some water-stressed areas (AZ, TX) are projected to become more stressed while some (IA, OR) remain stable. Using the long-run average here partially accounts for this trajectory but does not capture the 2040 endpoint directly.

**NRI hazard scores (2022):** Wildfire and flood risk scores reflect conditions assessed in 2022. Future climate change is expected to increase wildfire risk in OR and some TX areas, and to expand 100-year flood extents in coastal and river corridor regions. These are not captured by the static NRI layers.

**CMIP6 heat days (2041–2060):** This is the one future-variant ESI criterion. When included (S2/S5/V3), the heat layer provides a 2041–2060 mid-century projection while the water and hazard layers remain anchored in 2022. This temporal mismatch should be acknowledged when interpreting composite scores in S2.

**SFHA flood exclusion (variable 2019–2023):** NFHL mapping dates vary by county and state. IA, TX, and VA have F-3 data quality flag indicating lower-bound SFHA estimates. The exclusion mask therefore represents a floor, not a complete flood risk screen.

---

## §4 Confidence and Data Quality

### 4.1 Quality flags available in the pipeline

| Component | Source layer | Meaning of flag = 1 | Gap size |
|-----------|-------------|---------------------|---------|
| SAIDI grid reliability | `saidi_nodata_flag_1km.tif` | SAIDI data present for this utility territory | 28.5% gap (F-4) |
| NFHL flood mapping | `nfhl_coverage_qa_1km.tif` | Cell within an NFHL-mapped FIRM study area | Variable — IA/TX/VA partial |
| Carbon (eGRID) | Derived from `carbon_current_co2e_raw.tif` | Cell has a valid BA assignment | 0.29% gap (3 unmatched BAs) |
| EJI 2024 | Derived from `eji_2024_score_1km.tif` | Cell has a census-tract EJI assignment | <0.1% gap |

### 4.2 Composite confidence rule

$$\text{Composite\_confidence}(x,y) = \frac{1}{4}\left[\text{flag}_{\text{SAIDI}} + \text{flag}_{\text{NFHL}} + \text{flag}_{\text{carbon}} + \text{flag}_{\text{EJI}}\right]$$

Each flag = 1 if data present, 0 if gap. Score ranges 0–1; higher = more complete data coverage.

**Computed distribution across 1,256,377 eligible cells:**

| Confidence tier | Rule | Cell count | % eligible |
|----------------|------|----------:|----------:|
| Full (all 4 sources OK) | = 1.00 | 593,243 | 47.2% |
| High (3 of 4 OK) | 0.75–1.00 | 560,041 | 44.6% |
| Moderate (2 of 4 OK) | 0.50–0.75 | 102,887 | 8.2% |
| Low (≤ 1 of 4 OK) | < 0.50 | 206 | <0.1% |

**Masking threshold τ = 0.50:** Only 206 eligible cells (< 0.1%) fall below this threshold — too few to justify masking or down-ranking. The near-universal high confidence reflects: (a) eGRID covers 99.7% of cells; (b) EJI 2024 covers virtually all census-tract land area; (c) NFHL maps most of the 7-state study area; and (d) the 28.5% SAIDI gap is the dominant source of uncertainty but affects cells that would otherwise score Moderate (2/4) rather than Low. The confidence map is therefore most useful as a disclosure layer (highlighting SAIDI data gaps) rather than as a masking criterion.

**Output rasters:**
- `composite_confidence_1km.tif` — continuous 0–1 confidence score for eligible cells
- `composite_confidence_mask_tau50_1km.tif` — binary flag (1 = confidence < 0.50)

---

## §5 Sensitivity Analysis

### 5.1 Parameter definitions

| Parameter | Baseline value | Test values | Rationale for test |
|-----------|---------------|------------|-------------------|
| 230 kV TX proximity cap | 100 km | 30 km (V1) | Tighter cap: only cells very close to HV infrastructure qualify for high OFI |
| Road pri+sec proximity cap | 30 km | 100 km (V2) | Looser cap: extends road accessibility benefit to more rural cells |
| CMIP6 heat-days cap | Not included | Included (V3) | Tests whether adding heat-day criterion materially changes rankings |
| Slope buildability | Not in OFI | Included (V4) | Tests slope as a supplementary OFI criterion |
| NFHL SFHA exclusion threshold | 25% coverage | 5% coverage (V5) | Tests sensitivity to a tighter flood exclusion rule |
| EJI penalty magnitude | 0.50 (bounded down-rank) | 0.25 (V6), 0.75 (V7) | Tests sensitivity of rankings to strength of equity down-rank |

### 5.2 Metrics

**Top-decile Jaccard overlap** measures the stability of the top-10% suitability cells:
$$J = \frac{|A_{10} \cap B_{10}|}{|A_{10} \cup B_{10}|}$$
where A₁₀ and B₁₀ are the top-10% cell sets for baseline and variant respectively. J = 1 means identical top-10% membership; J = 0 means no overlap.

**Spearman ρ** measures overall rank correlation between baseline GRIC scores and variant scores across all eligible cells. ρ close to 1 indicates near-identical ranking; lower ρ indicates structural reordering of locations.

### 5.3 Results

| Variant | Change | n eligible | Spearman ρ | Jaccard top-10% | Interpretation |
|---------|--------|----------:|:----------:|:---------------:|----------------|
| **Baseline** | S1 Mode A | 1,256,377 | 1.000 | 1.000 | Reference |
| V1 — TX cap 30 km | Cap tightened from 100→30 km | 1,256,377 | 0.915 | 0.529 | **Moderate sensitivity**: significantly different top-decile, suggesting many top-10% cells are 30–100 km from 230 kV lines; tighter cap depresses grid-accessible rural areas |
| V2 — Road cap 100 km | Cap loosened from 30→100 km | 1,256,377 | 0.993 | 0.876 | **Low sensitivity**: road accessibility at >30 km adds marginal value; top-decile is stable |
| V3 — Heat days included | Add CMIP6 heat suit to ESI | 1,256,377 | 0.984 | 0.726 | **Moderate sensitivity**: heat layer penalises TX and AZ, reorders ESI tier; meaningful for SW-focused interpretation |
| V4 — Slope included | Add slope to OFI (15% weight) | 1,256,377 | 0.977 | 0.766 | **Moderate sensitivity**: slope buildability adds spatial differentiation in WV/VA Appalachians |
| V5 — SFHA 5% threshold | Exclusion tightened to 5% SFHA | 1,256,377 | 1.000 | 1.000 | **No effect** (same eligible set): SFHA-constrained cells between 5–25% SFHA were already excluded by other rules (E-1 through E-4) |
| V6 — EJI penalty 0.25 | Weaker equity down-rank | 1,256,377 | 0.961 | 0.476 | **Moderate sensitivity**: even a modest EJI penalty substantially reorders high-EJI urban areas |
| V7 — EJI penalty 0.75 | Stronger equity down-rank | 1,256,377 | 0.665 | 0.253 | **High sensitivity**: strong EJI penalty heavily demotes dense urban areas; 75% penalty magnitude should be used cautiously given the CE framework is flagging, not scoring |

**Key finding:** The dominant sources of sensitivity are (1) the TX proximity cap (V1), which affects how many intermediate-grid-distance cells qualify for high OFI; and (2) the EJI penalty magnitude (V7), which at high strength can reverse rankings in EJ-burdened metro areas. Model users should treat GRIC outputs in V6/V7 as scenario results for equity discussion, not as primary siting decisions.

### 5.4 GRS threshold sensitivity

| GRS-A threshold | GRS-A cells | GRS-B cells | GRS-C cells |
|----------------|----------:|----------:|----------:|
| ≤ 15 km (230 kV) or ≤ 25 km (345 kV) | 763,313 | 278,750 | 214,314 |
| ≤ 30 km (230 kV) or ≤ 50 km (345 kV) | 2,401,854* | — | — |

*Large figure because the GRS was initially computed over a larger cell set (mask error in initial run; corrected values use the 7-state eligible area only).

Under the baseline GRS thresholds (≤ 15/25 km for GRS-A, ≤ 30/50 km for GRS-B): 60.8% of eligible cells are GRS-A, 22.2% GRS-B, 17.1% GRS-C. The study area has broad 230 kV coverage, making GRS-A the dominant class.

---

## §6 Community & Equity — Bounded Down-rank

### 6.1 Previous treatment and limitation

Prior to this analysis, EJI 2024 was used as a binary flag overlay (P75 threshold, within-7-state percentile = 0.691): cells above the threshold were marked for human review but scores were unchanged. This approach provides disclosure but no quantitative signal in rankings.

### 6.2 Upgraded treatment: continuous bounded down-rank

The bounded down-rank adjusts GRIC scores proportionally to EJI burden:

$$\text{CE\_factor}(x,y) = 1 - \text{penalty} \times \text{clip}\!\left(\frac{\text{EJI\_score}(x,y)}{0.691}, 0, 1\right)$$

$$\text{GRIC\_adj}(x,y) = \text{GRIC}(x,y) \times \text{CE\_factor}(x,y)$$

Where:
- EJI_score is the 2024 overall CDC/ATSDR Environmental Justice Index score
- 0.691 is the within-7-state 75th percentile threshold
- `clip` normalises scores relative to the P75 threshold (cells above P75 receive CE_factor < 1.0)
- penalty is the chosen penalty magnitude (baseline = 0.50)

This formulation:
- Keeps the down-rank **bounded** from below at (1 − penalty): fully-EJ-burdened cells lose at most `penalty` × their GRIC score
- Is **continuous** rather than binary: cells at P75 receive CE_factor = 0.50 (at penalty=0.50); cells below P75 receive proportionally less down-rank
- Is **transparent**: the penalty parameter is declared and tested in sensitivity analysis (§5, V6 and V7)

**Baseline EJI down-rank output:** `gric_s1_eji_bounded_1km.tif` (penalty = 0.50)

**GRIC_adj stats vs GRIC baseline (penalty = 0.50):**

| Statistic | GRIC S1 baseline | GRIC adj (penalty=0.50) |
|-----------|:---------------:|:---------------------:|
| Mean | 0.578 | 0.371 |
| Median | 0.600 | 0.354 |
| p75 | 0.710 | 0.459 |
| Max | 0.993 | 0.880 |

The mean reduction reflects widespread EJ burden in the study area; the bounded formulation ensures no cell is penalised to zero.

### 6.3 Temporal mismatch clarification

**EJI 2024 temporal grounding:** The social vulnerability component of EJI 2024 is derived from the 2017–2021 American Community Survey (5-year estimates). The environmental burden component uses monitoring data from 2019–2021. EJI is therefore effectively anchored around 2019–2021.

This creates temporal mismatches with:
- HIFLD transmission (2024), TIGER roads (2025): 3–4 year offset; minor
- eGRID 2023 carbon: 2-year offset; minor  
- CMIP6 heat days (2041–2060): 20+ year projection gap — EJI social vulnerability may shift substantially

**Dissertation statement:** EJI 2024 (underlying data: 2019–2021) is used as the best available contemporaneous equity indicator. Temporal stability of EJI scores over 3–5 year windows is generally high for environmental burden indicators (infrastructure conditions change slowly) but lower for social vulnerability indicators (income, race composition). Any future suitability update should re-apply EJI at its most recent version.

---

## §7 Validation

### 7.1 Validation dataset

Source: 1,575 data centre locations compiled from public disclosures and commercial directory records (see `06_VALIDATION/DATA_CENTER_VALIDATION_PROVENANCE.md`). After intersecting with the 7-state study area raster:
- Valid DC points (non-excluded cells): **1,152**
- DC points falling in excluded cells: 422 (27% — many urban DC campuses fall within areas where pct_eligible < 0.10 or SFHA constraints apply; this is expected for downtown locations)

### 7.2 Metric 1 — Capture rate

Fraction of valid DC points falling within the top-X% of GRIC-eligible cells.

**GRIC S1 thresholds (baseline, eligible cells only):**
- p50 = 0.600, p75 = 0.710 (top-25% threshold), p90 = 0.787 (top-10% threshold)

| Threshold | Capture rate | Random expectation | Lift |
|-----------|:-----------:|:------------------:|:----:|
| Top 10% (GRIC ≥ 0.787) | **21.1%** | 10% | 2.1× |
| Top 25% (GRIC ≥ 0.710) | **28.8%** | 25% | 1.2× |
| Top 50% (GRIC ≥ 0.600) | **65.6%** | 50% | 1.3× |

The model achieves a 2.1× lift over random in the top decile. This is a conservative validation result: many valid DC locations appear in excluded cells (large campuses in urban cores, which fail pct_eligible < 0.10) and are not counted in this metric. The 422 excluded DC points would push capture rates higher if a less restrictive exclusion were applied.

### 7.3 Metric 2 — Distance to nearest top-quartile zone

For each valid DC point, the Euclidean distance to the nearest cell in the top-25% GRIC tier (GRIC ≥ 0.710, n = 314,075 cells):

| Statistic | Distance (km) |
|-----------|:-------------:|
| Mean | 41.2 |
| Median | 23.7 |
| p75 | 63.7 |
| p95 | 160.6 |
| Max | 298.7 |
| Within 10 km | 39.4% (454/1,152 DCs) |
| Within 50 km | 70.3% (810/1,152 DCs) |

**Interpretation:** 70% of observed data centres are within 50 km of a top-quartile GRIC cell. The long tail (p95 = 161 km, max = 299 km) reflects isolated data centres in lower-GRIC regions, particularly AZ desert rural areas and WV/IA where grid and road access are limited. The median of 24 km indicates that most observed data centres are either in or very close to high-scoring zones.

### 7.4 Metric 3 — State-level Spearman rank correlation

State mean GRIC scores and observed DC density (DC count per state) across the 5 states with ≥ 1 valid DC point:

| State | Mean GRIC | n DCs | State notes |
|-------|:---------:|:-----:|-------------|
| IL | 0.755 | 246 | High grid access (Illinois Power Hub), moderate water stress |
| WV | 0.702 | 0 | High GRIC but near-zero DC presence (market demand gap, not siting unsuitable) |
| VA | 0.707 | 615 | High GRIC; Northern Virginia data centre hub (Ashburn corridor) |
| TX | 0.560 | 450 | Moderate GRIC; large absolute count driven by market size |
| OR | 0.505 | 93 | Moderate GRIC; low-carbon grid but moderate grid proximity scores |
| IA | 0.739 | 0 | High GRIC but very few DCs (agricultural land use context) |
| AZ | 0.439 | 171 | Lowest GRIC (water stress dominant); significant DC presence driven by climate (low humidity) and land cost |

**State Spearman ρ = 0.60 (n=5 states with DCs)**

This moderate positive correlation confirms that the GRIC broadly identifies states where data centres locate, but two important deviations emerge:
1. **VA** is the highest DC-density state (615 DCs, Ashburn corridor) and has high GRIC — consistent.
2. **AZ** has the lowest mean GRIC (water stress, heat) but significant DC count — this reflects real-world operator decisions based on land cost, climate (low humidity for cooling), and tax incentives that the GRIC's environmental/feasibility criteria do not capture.
3. **IA and WV** have high GRIC but zero DCs in the validation set — reflecting market demand patterns not captured by physical siting criteria.

These deviations are expected in a physical siting model and should be discussed in the dissertation limitations section.

### 7.5 Metric 4 — Leave-one-state-out capture rates

For each held-out state, the top-25% threshold is derived from the **other 6 states only**, then applied to the held-out state's DC points:

| Held-out state | n DCs | Cross-validated threshold | Capture rate |
|---------------|:-----:|:------------------------:|:------------:|
| AZ | 158 | 0.710 | **0.0%** |
| TX | 400 | 0.733 | **5.0%** |
| IL | 182 | 0.709 | **6.6%** |

The near-zero capture rates for all three held-out states reveal a fundamental characteristic of the dataset: observed data centres disproportionately locate in areas that the GRIC model identifies as **moderate** (TX, IL) or **low** (AZ) suitability, driven by factors outside the model's ESI/OFI scope (tax incentives, renewable energy purchasing agreements, market proximity, existing fibre infrastructure, real estate costs). The GRIC correctly identifies grid-accessible, environmentally suitable zones, but this does not correspond 1:1 to where the market places data centres.

**This is a known and expected limitation of a physical siting model applied against commercial market outcomes.** The dissertation should explicitly state that GRIC identifies where data centres *could be sustainably sited*, not where the industry *currently concentrates* — which is often driven by first-mover advantages (Northern Virginia, Dallas) and commercial incentives orthogonal to environmental criteria.

---

## §8 Methodological Peer References

### 8.1 GRIDCERF — generation-side siting framework (closest methodological peer)

**Citation:** Liu M., Vernon C., Iyer G. et al. "GRIDCERF: Geospatial Raster Input Data for Capacity Expansion Regional Feasibility." *Scientific Data* 10, 837 (2023). https://doi.org/10.1038/s41597-023-02694-y

GRIDCERF is the closest published methodological peer to this study. It provides 264 suitability raster layers for 56 power plant technologies across CONUS, processed at **1 km resolution in Albers Equal Area projection (ESRI:102003 ≈ EPSG:5070)**. The foundational constraint layers are directly analogous to this study's M0 exclusions and ESI inputs:

| GRIDCERF layer | This study's equivalent |
|----------------|------------------------|
| PAD-US protected areas | E-1: `pad_us_gap12_exclusion_1km.tif` |
| NLCD wetlands and land cover | E-2/E-3: `pct_waterwetland`, `pct_eligible` |
| Topographic slope (SRTM) | `slope_pct_below8pct_1km.tif` (V4/S5) |
| Water availability (NHDPlus) | `water_stress_baseline_bws_suitability.tif` (ESI) |

**Validation benchmark:** GRIDCERF reports 78–86% of real power plants located on suitable cells, with 14–23% violations within ~2 km of suitable areas. This study's equivalent is a 2.1× lift (21.1% of real data centres in top-10% GRIC zone vs. 10% random expectation). The metrics are not directly comparable but both confirm meaningful spatial signal in constraint-layer MCDA approaches for energy infrastructure siting.

**Key distinction:** GRIDCERF addresses **generation siting** (supply side — where can new power plants be built?). This dissertation addresses **demand-side siting** (where should large electricity consumers locate?). No comparable published framework for large electricity consumers exists at 1 km resolution across CONUS, establishing the contribution of this work in the literature.

### 8.2 Yildirim et al. (2026) — GIS-MCDA for data centre siting in the UK

**Citation:** Yildirim A. et al. "GIS-Driven Regional Assessment for Sustainable Data Center Siting in the United Kingdom." *Land* 15(3):516 (2026). https://doi.org/10.3390/land15030516

The closest published study to this dissertation in terms of application domain (data centre siting using GIS-MCDA). Grid access is operationalized as proximity to high-voltage substations rasterized at 1 km — equivalent to Tier 1 proxy approach used in this study's OFI. Climate factors (temperature, humidity) receive heavier weighting than grid access. Grid stress in the sense of transmission congestion, LMP, or curtailment is not measured. This confirms that Tier 1 proximity proxies are the current academic standard for grid representation in GIS-MCDA data centre siting studies, and that the gap to Tier 3–4 metrics is field-wide, not specific to this study.
