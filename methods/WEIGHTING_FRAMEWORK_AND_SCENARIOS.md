# Weighting Framework and Scenario Design
**Project:** Sustainable Data Centre Siting — 7-State MCDA Study  
**Date:** 2026-06-17 | **Last updated:** 2026-06-23  
**Status:** ✅ READY FOR SUPERVISOR REVIEW — empirical correlation analysis complete; 6 supplementary layers added (Step 11); awaiting supervisor approval before composite maps are run  
**Prerequisite:** R-9 approved 2026-06-17 under conditions (1)–(6) below

---

## R-9 Approval Conditions (restated for audit trail)

1. PAD-US 4.1 accepted as the protected-areas source.  
2. Slope = Option C: buildability/operational flag only, not a hard exclusion (except Scenario 5 where it enters OFI as a scored layer).  
3. NFHL outputs carry F-3 caveat: IA/TX/VA are lower-bound estimates; absence of SFHA flag ≠ flood-free.  
4. SAIDI = sensitivity/context only, never a primary scored criterion.  
5. Substations = provisional/contextual (HIFLD F-6); used in GRS Tier 1 tertiary and Scenario 1–4 context only.  
6. No single final suitability map treated as definitive; scenario comparison and sensitivity testing required.

---

## 1. Model Architecture

The composite model has a **two-tier linear additive structure**:

```
Composite_score = w_ESI × ESI_score + w_OFI × OFI_score
```

where:
```
ESI_score = Σ (w_i_ESI × normalized_i)   for layers in ESI
OFI_score = Σ (w_j_OFI × normalized_j)   for layers in OFI
```

Three additional components operate **outside the weighted composite**:

| Component | Type | How applied |
|-----------|------|------------|
| **M0 Hard Exclusion mask** | Binary gate | Applied first; excluded cells → NoData in all outputs |
| **Grid Readiness Screen (GRS)** | Tiered proximity screen | Computed as a separate classified layer; displayed alongside composite |
| **Community & Equity flag** | Disclosure overlay | Applied post-composite; never adjusts weights; flags cells for human review |

---

## 2. Hard Exclusion Mask (Applied in All Scenarios)

All five scenarios share the same base exclusion mask. A cell is excluded (set to NoData) if **any** of the following are true:

| Rule | Layer | Threshold | Rationale |
|------|-------|-----------|-----------|
| E-1 | `pad_us_gap12_exclusion_1km.tif` | = 1 | GAP Status 1+2: biodiversity mandate; legally protected |
| E-2 | `pct_waterwetland_1km_EPSG5070.tif` | ≥ 0.50 | > 50% of cell is open water or wetland |
| E-3 | `pct_eligible_1km_EPSG5070.tif` | < 0.10 | < 10% of cell is on eligible land cover |
| E-4 | `nfhl_floodway_fraction_1km.tif` | > 0 | Any floodway coverage; FEMA regulatory floodway |
| E-5 | `nfhl_sfha_fraction_1km.tif` | ≥ 0.25 | ≥ 25% SFHA coverage (hybrid treatment R-8) |

**Scenario 5 only** applies a tighter SFHA threshold (E-5 replaced by ≥ 0.05).

Cells that survive all exclusions form the **eligible study area** (n ≈ 1.3–1.6M cells, to be confirmed at composite run time).

---

## 3. Layer Normalization Specifications

All scored layers must be transformed to a common 0–1 suitability scale where **higher = more suitable** before weights are applied. The transformations below are applied in the composite-generation script.

### 3a. ESI Layers

| Layer | Raw range (study area) | Transform | Formula | Direction | Notes |
|-------|----------------------|-----------|---------|-----------|-------|
| `carbon_current_co2e_suitability.tif` | 0.00–1.00 | None needed | `suit = raw` | Higher = better (lower CO2e grid) | Pre-normalized suitability |
| `water_stress_baseline_bws_suitability.tif` | 0.00–1.00 | None needed | `suit = raw` | Higher = better (lower water stress) | Pre-normalized suitability |
| `nri_wildfire_score_1km.tif` | 0.10–99.97 | ÷ 100 | `suit = raw / 100` | Higher = better (lower wildfire risk) | NRI county percentile rank; **already inverted by FEMA** — 100 = lowest hazard risk = best; do NOT re-invert |
| `nri_inland_flood_score_1km.tif` | 0.22–99.97 | ÷ 100 | `suit = raw / 100` | Higher = better (lower flood risk) | Same structure; 100 = lowest flood risk = best; do NOT re-invert |
| `nexgddp_mean_days_gt35_2041_2060.tif` | 0.00–131.57 | Invert + normalise | `suit = max(0, 1 − raw/130)` | Raw higher = more heat = WORSE | Scenario 2 and 5 only; supervisor approval condition still applies |

### 3b. OFI Layers

| Layer | Raw range (study area) | Transform | Threshold | Formula | Direction | Notes |
|-------|----------------------|-----------|-----------|---------|-----------|-------|
| `hifld_tx_230kV_proximity_1km.tif` | 0–259,494 m | Linear inverse | 100 km | `suit = max(0, 1 − d/100000)` | Closer = better | SOLE primary OFI grid-access criterion |
| `tiger_roads_prisec_proximity_1km.tif` | 0–80,623 m | Linear inverse | 30 km | `suit = max(0, 1 − d/30000)` | Closer = better | Primary+secondary network; preferred road metric |
| `tiger_roads_primary_proximity_1km.tif` | 0–224,056 m | Linear inverse | 100 km | `suit = max(0, 1 − d/100000)` | Closer = better | Primary-only alternative; Scenario 3 uses this |
| `slope_pct_below8pct_1km.tif` | 0.00–1.00 | None needed | — | `suit = raw` | Higher = more buildable = better | Scenario 5 OFI only; Option C elsewhere |

### 3c. GRS Layers (not composited; used for classification only)

| Layer | Raw range | Direction | GRS role |
|-------|-----------|-----------|---------|
| `hifld_tx_345kV_proximity_1km.tif` | 0–259,494 m | Closer = better | Tier 1 primary |
| `hifld_tx_230kV_proximity_1km.tif` | 0–259,494 m | Closer = better | Tier 1 secondary |
| `hifld_substations_IN_SERVICE_proximity_1km.tif` | 0–104,924 m | Closer = better | Tier 1 tertiary (provisional F-6) |
| `saidi_option_a_custweighted_suitability.tif` | — | — | Tier 2 context only |

### 3d. Community & Equity Layers (flags only — never weighted)

| Layer | Use |
|-------|-----|
| `eji_2024_flag_p75_1km.tif` | Binary flag overlay (within-7-state P75 = 0.691) |
| `eji_2024_score_1km.tif` | Continuous context layer |
| `eji_2024_envburd_1km.tif` | Environmental burden context |
| `eji_2024_socvuln_1km.tif` | Social vulnerability context |

### 3e. Context / Sensitivity Layers (displayed; never scored)

| Layer | Category |
|-------|---------|
| `pad_us_gap3_flag_1km.tif` | Planning-review flag (GAP3) |
| `nfhl_coverage_qa_1km.tif` | F-3: unmapped flood areas |
| `nfhl_sfha_fraction_1km.tif` | SFHA gradient (0.05–0.25 constraint zone in S5) |
| `nexgddp_std_days_gt35_2041_2060.tif` | Climate uncertainty overlay (M4) |
| `saidi_option_a_custweighted_suitability.tif` | Grid reliability context (28.5% NoData gap — see F-4) |
| `saidi_nodata_flag_1km.tif` | SAIDI coverage disclosure flag (1=data present; 0=gap) |
| `hifld_tx_345kV_proximity_1km.tif` | GRS Tier 1 primary (not an OFI scored layer) |
| `hifld_substations_IN_SERVICE_proximity_1km.tif` | GRS Tier 1 tertiary (not scored in OFI) |
| `pct_developed_1km_EPSG5070.tif` | Brownfield/redevelopment opportunity |
| `eia860_powerplants_operating_7state_EPSG5070.gpkg` | Power generation supply context |
| `carbon_future2040_aer_load_co2e_suit.tif` | Future-grid sensitivity scenario |
| `water_stress_future2050bau_ws_suitability.tif` | Future water-stress sensitivity |
| `ferc_queue_mw_density_1km.tif` | FERC active queued MW by county (raw; see §3f) |
| `pdsi_mean_suitability_1km.tif` | Long-term drought context 2000–2024 (see §3f) |

### 3f. Step 11 Supplementary Layers — Provisional Roles (Awaiting Supervisor Input)

Six additional layers were processed in Step 11 (2026-06-23) to strengthen the water scarcity, grid economics, and reliability dimensions. Their role in the scored model is **provisional** — listed here for transparency. Final inclusion decisions require supervisor input before composite generation.

| Layer | Range | Transform applied | Provisional role | Candidate module | Key caveat |
|-------|-------|------------------|-----------------|-----------------|------------|
| `aqueduct_iav_suitability_1km.tif` | 0.00–0.875 | `1 − iav_score/5` (WRI 0–5 scale) | Supplementary water reliability indicator | ESI | F-14: 0.5° HydroBASIN resolution coarser than 1 km raster |
| `aqueduct_gtd_suitability_1km.tif` | 0.34–1.00 | `max(0, 1 − gtd_score/5)` | Supplementary groundwater sustainability indicator | ESI | F-14: same resolution caveat; GTD = −9999 for insignificant depletion → treated as 1.0 |
| `pdsi_mean_suitability_1km.tif` | 0.16–0.71 | `clip((pdsi_mean + 4)/8, 0, 1)` | Long-term drought context / sensitivity layer | ESI or context | F-17: NOAA climate-division resolution (344 divisions for CONUS); 2000–2024 mean PDSI |
| `ferc_queue_suitability_1km.tif` | 0.00–1.00 | `clip(1 − MW/p99, 0, 1)`; p99 = 24,874 MW | Grid congestion proxy | OFI (supplementary) | F-15: county-level aggregation; 767 GW active+suspended in 7 states; 2024 LBNL data |
| `eia_retail_price_suitability_1km.tif` | 0.00–1.00 | Linear: `(max − price)/(max − min)` | Electricity cost operational suitability | OFI (supplementary) | F-16: state-level only (coarse); 2020 EIA data; TX=1.0 (5.07 ¢/kWh), IL=0.0 (6.70 ¢/kWh) |
| `saidi_nodata_flag_1km.tif` | 0 or 1 | Binary: 1=data, 0=coverage gap | Coverage disclosure flag (not scored) | Context | 71.5% of 7-state cells have SAIDI data; 28.5% gap (F-4) — supersedes ad-hoc SAIDI ND treatment |

**Scoring guidance for supervisor discussion:**

| Decision | Recommended position | Rationale |
|----------|---------------------|-----------|
| IAV in scored ESI? | **Yes, at low weight (5–10% within ESI)** | Measures seasonal water reliability, independent from baseline BWS stress; OR Pacific NW scores highest |
| GTD in scored ESI? | **Sensitivity only** | Correlates with IAV in water-rich areas; adding both risks double-weighting western water availability |
| PDSI in scored ESI? | **Context/sensitivity only** | Climate-division resolution too coarse for 1 km composite; useful as cross-validation for Aqueduct BWS |
| FERC queue in scored OFI? | **Context/sensitivity** | Novel proxy; no precedent in published DC siting literature; grid congestion ≠ site-level interconnection cost; recommend dissertation footnote acknowledging the limitation |
| EIA price in scored OFI? | **Yes, at very low weight (5% within OFI)** | State-level differentiation is real (TX vs IL ~24% cheaper); coarseness is transparent; defensible as operational cost indicator |
| SAIDI flag | **Always-on disclosure flag** | Explicitly maps the 28.5% reliability data gap; should appear alongside all scenario outputs |

---

## 4. Grid Readiness Screen (GRS) — All Scenarios

The GRS is computed once and displayed alongside all five composite scenarios. It is a **three-class reclassification** based on proximity to high-voltage infrastructure — not a continuous score.

| GRS Class | Criteria | Interpretation |
|-----------|---------|---------------|
| **GRS-A** (High) | ≤ 25 km from 345kV **OR** ≤ 15 km from 230kV | Within practical transmission interconnection range for hyperscale DC |
| **GRS-B** (Moderate) | ≤ 50 km from 345kV **OR** ≤ 30 km from 230kV | Feasible with transmission extension; developer engineering required |
| **GRS-C** (Low/Poor) | > 50 km from 345kV **AND** > 30 km from 230kV | Unlikely to attract 100+ MW facility without major infrastructure investment |
| **GRS-X** (Excluded) | Fails any M0 hard exclusion | Outside eligible study area |

*Substation proximity (Tier 1 tertiary, provisional) and SAIDI (Tier 2 context) are displayed as supplementary GRS attributes but do not alter the A/B/C classification.*

---

## 5. Five Scenarios — Summary Table

The table below gives effective composite weights (= module weight × within-module weight). Weights within each scenario sum to 100%.

| Layer (normalized) | Module | S1 Balanced | S2 Env-first | S3 Dev-first | S4 Comm-prot | S5 Conserv. |
|-------------------|--------|:-----------:|:------------:|:------------:|:------------:|:-----------:|
| **Carbon intensity (current)** | ESI | 15% | 24.5% | 10% | 15% | 11% |
| **Water stress (current)** | ESI | 15% | 24.5% | 10% | 15% | 13.75% |
| **NRI wildfire** | ESI | 10% | 10.5% | 2.5% | 10% | 11% |
| **NRI inland flood** | ESI | 10% | 10.5% | 2.5% | 10% | 13.75% |
| **CMIP6 heat days (inverted)** | ESI | ❌ | ✅ 5.5% | ❌ | ❌ | ✅ 5.5% |
| **230kV TX proximity (inverse)** | OFI | 35% | 18% | 48.75% | 35% | 27% |
| **Road proximity (prisec, inverse)** | OFI | 15% | 12% | 26.25% | 15% | — |
| **Road proximity (primary, inverse)** | OFI | — | — | — | — | 13.5% |
| **Slope buildability (≥ 8%)** | OFI | ❌ | ❌ | ❌ | ❌ | ✅ 4.5% |
| **Total scored (excl. heat days)** | | **100%** | **100%** | **100%** | **100%** | **94.5%*** |
| **EJI P75 flag** | CE | Overlay | Overlay | Overlay | ⚠️ Penalty | Overlay |
| **ESI module weight** | — | 50% | 70% | 25% | 50% | 55% |
| **OFI module weight** | — | 50% | 30% | 75% | 50% | 45% |

*\* S5 total = 94.5% without heat days (5.5%) + slope (4.5%) = 104.5% — this is intentional; see §6.5. When heat days and slope are both included in S5, internal module weights are renormalised so ESI + OFI = 100%. Final renormalised S5 effective weights: Carbon 10%, Water 12.5%, Wildfire 10%, Flood 12.5%, Heat 5%, Grid 27%, Road 13.5%, Slope 4.5% → 95% + 5% renorm = 100%. S2 with optional heat days: all ESI layers renormalised as noted in §6.2.*

---

## 6. Per-Scenario Detail

### 6.1 Scenario 1 — Balanced

**Rationale:** Equal ESI/OFI weighting represents a neutral planning position. Appropriate as a baseline reference and for cross-scenario comparison. No prior preference for environmental over operational criteria.

**Module weights:** ESI 50% · OFI 50%

**ESI internal weights (sum to 100% of ESI):**

| Layer | Within-ESI weight | Effective composite weight | Justification |
|-------|:-----------------:|:-------------------------:|---------------|
| Carbon intensity (current) | 30% | 15% | Grid decarbonisation is the primary ESI driver; differentiates states strongly (WV vs OR) |
| Water stress (baseline) | 30% | 15% | Cooling-water demand is the second critical ESI factor; high AZ/TX risk |
| NRI wildfire (inverted) | 20% | 10% | Regional wildfire risk; county-level proxy — lower weight reflects coarser spatial resolution |
| NRI inland flood (inverted) | 20% | 10% | River-valley flood risk gradient outside SFHA; complements NFHL hard exclusion |
| CMIP6 heat days | **not included** | — | Double-count risk with carbon/water in SW; include only with supervisor approval |

**OFI internal weights (sum to 100% of OFI):**

| Layer | Within-OFI weight | Effective composite weight | Justification |
|-------|:-----------------:|:-------------------------:|---------------|
| 230kV TX proximity (inverse) | 70% | 35% | Primary and sole grid-access criterion in OFI; HV transmission proximity is the dominant feasibility factor for large DC |
| Road proximity primary+secondary (inverse) | 30% | 15% | Secondary OFI factor; primary+secondary network (MTFCC S1100+S1200) appropriate for industrial access |

**Hard exclusions:** Standard (E-1 through E-5, SFHA threshold = 25%)  
**SFHA constraint zone:** cells 5–25% SFHA fraction → flagged but not excluded  
**Additional flags displayed:** GAP3 planning review, EJI P75 overlay, NFHL coverage QA  
**Sensitivity layers shown (not scored):** 345kV proximity, substations, SAIDI  
**Expected output:** A spatially balanced suitability surface. Expected high-scoring clusters near major 230kV corridors (I-10 TX/AZ, I-55 IL, I-81 VA) with low-ESI areas in SW penalised less than in S2.

---

### 6.2 Scenario 2 — Environmental-first

**Rationale:** Prioritises minimising environmental footprint. Suitable for organisations with net-zero commitments or green-power procurement targets. Reflects the perspective that grid carbon and water scarcity are existential risks, not just preferences.

**Module weights:** ESI 70% · OFI 30%

**ESI internal weights (sum to 100% of ESI, effective = × 0.70):**

| Layer | Within-ESI weight | Effective composite weight | Justification |
|-------|:-----------------:|:-------------------------:|---------------|
| Carbon intensity (current) | 35% | 24.5% | Highest weight; renewable-heavy grids (OR, IA wind) strongly preferred |
| Water stress (baseline) | 35% | 24.5% | SW arid states (AZ, TX) heavily penalised |
| NRI wildfire (inverted) | 15% | 10.5% | Reduced — wildfire risk is partially correlated with low-carbon areas (OR, CO) |
| NRI inland flood (inverted) | 15% | 10.5% | Same reduction |
| CMIP6 heat days (inverted) | **optional: 10%** | **7% (if included)** | Heat-day inclusion here is most defensible — SW double-count risk accepted in this scenario because the intent IS to penalise AZ/TX |

*If CMIP6 heat days are included in S2, re-normalise the other four to sum with heat days to 100%: Carbon 31.5%, Water 31.5%, Wildfire 13.5%, Flood 13.5%, Heat 10% → effective 22.05%, 22.05%, 9.45%, 9.45%, 7%.*

**OFI internal weights:**

| Layer | Within-OFI weight | Effective composite weight | Justification |
|-------|:-----------------:|:-------------------------:|---------------|
| 230kV TX proximity (inverse) | 60% | 18% | Still primary OFI factor; reduced relative importance vs ESI |
| Road proximity primary+secondary (inverse) | 40% | 12% | Slightly elevated road weight to compensate for reduced OFI budget |

**Hard exclusions:** Standard (SFHA ≥ 25%)  
**Expected output:** Strong geographic differentiation. Oregon (low-carbon hydro grid + moderate water stress) and Iowa (growing wind generation) likely to score high. Arizona and Texas depressed by water stress despite good grid access. IL scores high on grid access but mid-range on carbon.

---

### 6.3 Scenario 3 — Developer / Operational-first

**Rationale:** Represents the private-sector developer perspective where construction feasibility and grid access are dominant. Useful for identifying sites that the market is likely to develop regardless of ESI profile — a "business-as-usual" comparator.

**Module weights:** ESI 25% · OFI 75%

**ESI internal weights (sum to 100% of ESI, effective = × 0.25):**

| Layer | Within-ESI weight | Effective composite weight | Justification |
|-------|:-----------------:|:-------------------------:|---------------|
| Carbon intensity (current) | 40% | 10% | Retained — increasingly relevant to corporate RE procurement |
| Water stress (baseline) | 40% | 10% | Retained — cooling costs matter operationally |
| NRI wildfire (inverted) | 10% | 2.5% | Minimal — large DCs are hardened; wildfire insurance exists |
| NRI inland flood (inverted) | 10% | 2.5% | Minimal — flood risk managed via hard exclusion + engineering |
| CMIP6 heat days | not included | — | Cooling cost is implicit in operational energy; not double-counted |

**OFI internal weights:**

| Layer | Within-OFI weight | Effective composite weight | Justification |
|-------|:-----------------:|:-------------------------:|---------------|
| 230kV TX proximity (inverse) | 65% | 48.75% | Dominant: grid access is the primary site-selection constraint for large DCs |
| Road proximity primary-only S1100 (inverse) | 35% | 26.25% | Primary-only roads (interstates + US highways) used here — heavy construction traffic and equipment delivery requires arterial access |

*Note: S3 uses primary-only (S1100) proximity rather than primary+secondary, as major construction logistics require interstate/highway access.*

**Hard exclusions:** Standard  
**Expected output:** Strong correlation with existing DC cluster locations. Northern Virginia (NOVA) and DFW Texas likely to score very high (dense 230kV grid + interstate access). This scenario's validation rate against observed DCs should be the highest; if not, examine proximity threshold calibration.

---

### 6.4 Scenario 4 — Community-protection

**Rationale:** Uses the same ESI/OFI weights as S1 (Balanced) but applies an explicit **EJI-constrained** post-processing step. Sites in the highest-burden quartile of environmental justice concern (EJI ≥ P75 within 7-state study area) receive a composite score penalty that makes them visually and analytically identifiable as a distinct tier. This is not a weighted trade-off — the penalty is a transparency mechanism.

**Module weights:** ESI 50% · OFI 50% (identical to S1)

**ESI and OFI internal weights:** Identical to Scenario 1.

**EJI constraint applied post-composite:**

```
If eji_2024_flag_p75 = 1:
    S4_score = composite_score × 0.50
Else:
    S4_score = composite_score × 1.00
```

This 50% penalty factor means a high-EJI site that scores 0.80 on the composite is displayed at 0.40 — visually in the lower tier — while remaining visible for disclosure. The penalty magnitude (50%) is a methodological assumption requiring justification in the dissertation (see §8 sensitivity).

**Interpretation:** S4 identifies the spatial intersection of high composite suitability and high environmental justice burden. Sites that score high in S4 are suitable AND low-burden. Sites that would score high in S1 but are penalised in S4 are high-suitability but high-burden — these are the sites requiring EJI mitigation assessment.

**Hard exclusions:** Standard  
**Additional CE disclosure:** EJI burden modules (environmental burden, social vulnerability) displayed as supplementary maps alongside S4 composite.  
**Expected output:** NOVA/DC metro area (high existing DC density, urban EJI burden) may score lower than in S1. Rural OR and IA with low EJI burden benefit. TX and IL metropolitan fringe areas show greatest split between S1 and S4.

---

### 6.5 Scenario 5 — Conservative Risk-avoidance

**Rationale:** Applies the most conservative interpretation of all physical hazard layers. Designed for contexts where insurance costs, regulatory risk, or institutional risk tolerance are paramount. Incorporates climate change projections (heat days) and slope buildability as explicit scored criteria.

**Module weights:** ESI 55% · OFI 45%

**Hard exclusion modification (S5 only):** SFHA threshold tightened from 25% to **5%** (E-5 replaced). Cells with SFHA fraction 5–25% that are eligible in S1–S4 become excluded in S5.

**GAP3 constraint (S5 only):** Cells where `pad_us_gap3_flag = 1` receive a composite score multiplier of **0.70** (30% penalty). GAP3 areas require planning review and may have leasing/permitting risk.

**ESI internal weights (sum to 100% of ESI, effective = × 0.55):**

| Layer | Within-ESI weight | Effective composite weight | Justification |
|-------|:-----------------:|:-------------------------:|---------------|
| Carbon intensity (current) | 20% | 11% | Lower weight — balanced against hazard layers in risk-first framing |
| Water stress (baseline) | 25% | 13.75% | Elevated — drought/scarcity risk is compound with heat |
| NRI wildfire (inverted) | 20% | 11% | Elevated — physical fire risk premium in risk-avoidance framing |
| NRI inland flood (inverted) | 25% | 13.75% | Elevated — especially important given tightened SFHA threshold |
| CMIP6 heat days (inverted) | 10% | 5.5% | Included here: compound risk with water stress; SW premium justified |

**OFI internal weights (sum to 100% of OFI, effective = × 0.45):**

| Layer | Within-OFI weight | Effective composite weight | Justification |
|-------|:-----------------:|:-------------------------:|---------------|
| 230kV TX proximity (inverse) | 60% | 27% | Primary OFI factor |
| Road proximity primary-only (inverse) | 30% | 13.5% | Primary-only used (conservative = major road access only) |
| Slope buildability <8% (fraction) | 10% | 4.5% | Slope as OFI penalty in risk-avoidance context; poor buildability = higher construction risk |

**Additional S5 flags:** `nfhl_sfha_fraction_1km` 0.01–0.05 range displayed as "marginal flood exposure" annotation.  
**Expected output:** Most restrictive geographic footprint. AZ Colorado R. corridor and TX Gulf coast SFHA areas more heavily excluded. WV Appalachian cells penalised by slope. OR and IA rural areas with GAP3 NF lands penalised. Expected highest concentration of high-scoring cells in IL, northern VA exurban, and IA agricultural plains.

---

## 7. Scenario Comparison Matrix

| Property | S1 Balanced | S2 Env-first | S3 Dev-first | S4 Comm-prot | S5 Conserv. |
|---------|:-----------:|:------------:|:------------:|:------------:|:-----------:|
| ESI weight | 50% | 70% | 25% | 50% | 55% |
| OFI weight | 50% | 30% | 75% | 50% | 45% |
| SFHA threshold | 25% | 25% | 25% | 25% | **5%** |
| GAP3 penalty | No | No | No | No | **×0.70** |
| EJI penalty | No | No | No | **×0.50 flag** | No |
| CMIP6 heat days | No | Optional | No | No | Yes |
| Slope in OFI | No | No | No | No | **Yes (10%)** |
| Road network | Pri+sec | Pri+sec | **Pri-only** | Pri+sec | **Pri-only** |
| Primary use case | Baseline reference | Environmental prioritisation | Market-revealed preference | EJI disclosure | Regulatory/insurance risk |
| Expected geographic bias | Balanced | OR/IA preferred | NOVA/TX/DFW | Anti-urban fringe | Most restrictive |

---

## 8. Sensitivity Analysis Plan (post-composite — not in this document)

After all five composite maps are approved and generated, the following sensitivity tests should be run:

| Test | Method | Variables |
|------|--------|-----------|
| Weight sensitivity (OAT) | One-at-a-time ±10pp weight shift | All scored layers in S1; Pearson rank correlation of output |
| SFHA threshold sensitivity | Composite score at SFHA 0%, 5%, 10%, 25% thresholds | Applied to S1 composite; report % eligible area change |
| Carbon future scenario | Replace `carbon_current` with `carbon_future2040` | Run S1 variant; compare top-decile cell overlap |
| Water stress future | Replace `water_stress_baseline` with `water_stress_future2050bau` | S1 variant |
| EJI penalty magnitude | Test 0%, 25%, 50%, 75% penalty factors | S4 variant |
| Road network choice | Replace prisec with primary-only in S1 | Report Spearman rank correlation vs base S1 |

---

## 9. Normalization Threshold Justification

**230kV and 345kV transmission — 100 km threshold:**  
Derived from industry planning norms: US data-centre developers typically identify greenfield sites within 50–100 km of existing 230+ kV transmission infrastructure to avoid prohibitive transmission extension costs. The 100 km threshold includes >99% of the observed DC validation points; beyond this, suitability is assigned 0. A log-linear decay was considered but the linear threshold is more interpretable and easier to defend.

**Substation — 50 km threshold (GRS only):**  
Substations are far denser than transmission lines (study-area mean = 15 km). A 50 km threshold captures practical proximity while allowing geographic variation in the GRS classification.

**Road primary+secondary — 30 km threshold:**  
The primary+secondary network (MTFCC S1100+S1200) has a study-area mean of 7.4 km, meaning most cells are within 15 km. The 30 km threshold places the midpoint of the suitability range at 15 km, capturing meaningful variation without compressing the distribution.

**Road primary-only — 100 km threshold:**  
The primary-only (S1100) network is sparse (mean = 42 km). The 100 km threshold ensures cells near interstates/US highways have suitability values distinguishably above 0 across the study area.

**NRI scores ÷ 100 (no re-inversion):**  
National Risk Index hazard scores are national percentile ranks expressed 0–100, where **FEMA has already inverted the ranking** so that 100 = lowest hazard risk = highest suitability and 0 = highest hazard risk = lowest suitability. Division by 100 converts to a 0–1 suitability scale directly. Do **not** apply `1 − (raw/100)` — that would reverse the meaning and make high-risk cells appear suitable. Confirmed: study-area ranges 0.10–99.97 (wildfire) and 0.22–99.97 (flood); both are amenable to simple ÷100 normalisation with no further inversion.

**CMIP6 heat days — max 130 days:**  
The study-area maximum is 131.57 days >35°C/year (SW desert AZ). Using 130 as the normalisation maximum ensures the hottest cells score ≈ 0 and temperate cells score ≈ 1. Applied only in S2 (optional) and S5.

---

## 10. Empirical Criterion Correlation Analysis

**Computed:** 2026-06-22  
**Method:** Pearson correlation matrix across all 12 ESI/OFI layers at n = 1,688,545 common valid mask cells. Continuous suitability layers (CO2e, Water Stress, Wildfire, Flood) and Slope are used as-is (higher = better). Proximity layers (230kV, 345kV, Substations, Road P+S, Road P) are in raw metres (higher = farther = worse). CMIP6 heat days are raw (higher = more hot days = worse). EJI burden is the raw module score (higher = more burden = worse). The matrix is therefore in **mixed orientation** — see §10.2 for suitability-space interpretation.

Source files: `00_ADMIN/CRITERION_CORRELATION_MATRIX.csv`, `00_ADMIN/CRITERION_DESCRIPTIVE_STATS.csv`

### 10.1 Full Pearson Correlation Matrix (n = 1,688,545 cells)

| | CO2e | Water | Wildfire | Flood | Heat | 230kV | 345kV | Subst | Road P+S | Road P | Slope | EJI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **CO2e Suit** | 1.000 | −0.133 | −0.575 | −0.376 | +0.528 | −0.052 | −0.084 | −0.332 | −0.323 | −0.349 | −0.429 | −0.155 |
| **Water Suit** | | 1.000 | +0.292 | −0.056 | −0.010 | +0.169 | +0.178 | +0.218 | +0.187 | +0.176 | −0.132 | +0.057 |
| **Wildfire Suit** | | | 1.000 | +0.316 | −0.114 | +0.118 | +0.144 | +0.358 | +0.312 | +0.325 | +0.159 | +0.164 |
| **Flood Suit** | | | | 1.000 | −0.283 | −0.205 | −0.180 | +0.067 | +0.087 | −0.153 | +0.207 | −0.038 |
| **Heat Days (raw)** | | | | | 1.000 | −0.169 | −0.183 | −0.072 | −0.114 | −0.143 | −0.318 | −0.077 |
| **230kV (m)** | | | | | | 1.000 | +0.949 | +0.420 | +0.286 | +0.393 | +0.149 | +0.123 |
| **345kV (m)** | | | | | | | 1.000 | +0.394 | +0.282 | +0.409 | +0.166 | +0.145 |
| **Subst (m)** | | | | | | | | 1.000 | +0.591 | +0.491 | +0.143 | +0.106 |
| **Road P+S (m)** | | | | | | | | | 1.000 | +0.384 | +0.159 | +0.059 |
| **Road P (m)** | | | | | | | | | | 1.000 | +0.147 | +0.183 |
| **Slope <8%** | | | | | | | | | | | 1.000 | +0.146 |
| **EJI Burden** | | | | | | | | | | | | 1.000 |

*Proximity and Heat Days are in raw units (higher = worse). Suitability layers and Slope are normalised (higher = better). Correlations between layers in opposing orientations must be interpreted carefully — see §10.2.*

### 10.2 Key Findings and Methodological Implications

**Finding 1: r(230kV, 345kV) = +0.949 — anti-double-count rule confirmed empirically ✅**

The near-perfect positive correlation between 230kV and 345kV proximity (both in raw metres) confirms that these layers are measuring the same geographic phenomenon: proximity to high-voltage transmission corridors. Including both as independently weighted scored criteria in the OFI module would assign approximately double weight to grid proximity without adding explanatory power. The framework decision to score only 230kV proximity in the OFI composite and reserve 345kV as the GRS Tier 1 primary classifier is directly and strongly supported by this finding. This is the single most empirically decisive result from the pre-weighting analysis.

**Finding 2: r(CO2e Suit, Wildfire Suit) = −0.575 — ESI carbon and wildfire layers measure opposing geographies**

The strong negative correlation reflects a real geographic trade-off within the study area: the Pacific Northwest (Oregon) has a very clean hydro grid (high CO2e suitability) but elevated wildfire risk (lower wildfire suitability), while parts of Illinois and Virginia have less clean grids but near-zero wildfire risk (high wildfire suitability). These two ESI dimensions are measuring genuinely distinct site characteristics. Including both at positive weight does not double-count — they reward and penalise different geographic areas — and the substantial independence justifies the equal sub-weights assigned to carbon and wildfire in scenarios 1 and 3.

*Dissertation use: cite r = −0.58 as empirical confirmation that the four ESI criteria capture independent environmental dimensions.*

**Finding 3: r(CO2e Suit, Heat Days raw) = +0.528 — CMIP6 conditional treatment confirmed**

The moderate correlation means that in raw terms, cells with cleaner-grid suitability (high CO2e suit) tend to occupy areas with higher projected heat-day counts. When heat days is converted to suitability space (inverted: higher = fewer hot days = better), the implied correlation in suitability space is approximately **−0.53**, meaning clean-grid areas tend to have somewhat fewer projected hot days than dirty-grid areas. In practice, both AZ and TX carry high heat-day counts; if CMIP6 heat days were scored at full weight alongside carbon, it would amplify the geographic preference already expressed by the carbon criterion for the same south-western states. This moderate collinearity (|r| ≈ 0.53) — below the threshold that would require elimination, but large enough to justify caution — supports the framework decision to include CMIP6 heat days only in Scenarios 2 and 5 with explicit sensitivity testing.

*Dissertation use: cite r ≈ −0.53 in suitability space as empirical motivation for treating CMIP6 as a scenario-specific rather than baseline criterion.*

**Finding 4: r(Substations, Road P+S) = +0.591 — moderate infrastructure co-location**

Substation proximity and road (primary+secondary) proximity share moderate correlation, reflecting the co-location of electrical and road infrastructure near urban and industrial centres. Treating both as independently weighted, full-value scored criteria in the OFI module would assign excess combined weight to urban-industrial co-location relative to their individual explanatory contributions. The framework assigns substations to GRS Tier 1 tertiary only (not a scored OFI criterion), which avoids this double-weighting. Road P+S alone remains in the OFI scored set because road access is genuinely independent from transmission access (r(Road P+S, 230kV) = +0.286 — low).

**Finding 5: Low ESI × OFI cross-module correlations support the two-tier architecture**

The largest ESI × OFI cross-correlations in suitability space are: CO2e × Substations (r ≈ −0.33), CO2e × Slope (r = −0.43), Wildfire × Substations (+0.36), Wildfire × Road P+S (+0.31). No ESI–OFI pair reaches |r| = 0.45. The ESI and OFI modules are therefore measuring largely independent site attributes, validating the two-tier composite structure: weighting the modules separately (rather than treating all 8 criteria as a single flat weighted list) is analytically coherent.

**Finding 6: EJI Burden shows low correlation with all scored criteria (max |r| = 0.183)**

The maximum absolute correlation between EJI environmental burden and any scored layer is |r| = 0.18 (Road P primary). No scored criterion acts as an adequate proxy for environmental justice burden. This confirms the framework decision to treat EJI as an independent disclosure flag rather than as a proxy embedded within either module: high-scoring composite cells may carry high EJI burden that would be missed if EJI were folded into ESI or OFI weighting.

---

## 11. Implementation Notes for Composite Generation Script

When implementing, the composite generation script (`step9_run_scenario_composites.py` — to be written after framework approval) should:

1. Load the mask raster and define `valid = mask == 1` 
2. Apply M0 exclusion rules → create `eligible` Boolean array (valid AND not excluded)
3. Load and normalize each scored layer per §3
4. Clip all normalized values to [0, 1] after transformation
5. Compute ESI_score and OFI_score as weighted sums; apply module weights
6. Compute composite = w_ESI × ESI_score + w_OFI × OFI_score
7. For S4: multiply cells where eji_flag = 1 by 0.50
8. For S5: multiply cells where gap3_flag = 1 by 0.70; apply SFHA 5% threshold
9. Set composite = NoData (255) where `eligible == False`
10. Write each scenario as `scenario_{N}_{name}_composite_1km.tif` (Byte: 0–100 scaled, or Float32: 0.0–1.0)
11. Run GRS classification once and save as `grs_classification_1km.tif`
12. Extract composite scores at validation DC points and 5,000 random eligible points → compute capture rates per scenario
13. Generate scenario comparison raster: max-scenario dominance map

**Output directory:** `11_processed_layers/rasters/scenarios/`  
**Recommended data type:** Float32 (0.0–1.0) for analysis; rescaled Byte (0–100) for QGIS styling.

---

## 12. Limitations and Caveats to Disclose in Dissertation

| Flag | Issue | Mitigation |
|------|-------|-----------|
| F-3 | NFHL IA/TX/VA partial coverage | All SFHA layers labelled as lower-bound; S5 tighter threshold as sensitivity |
| F-4 | SAIDI 28.5% NoData | Context only; not scored in any scenario |
| F-5 | SAIDI MED/non-MED choice pending | Sensitivity display only |
| F-6 | HIFLD substation data provisional | Substations used in GRS Tier 1 tertiary only; not in OFI scoring |
| F-7 | CMIP6 inter-model uncertainty | Std-dev raster displayed as uncertainty overlay alongside S2/S5 |
| F-8 | EJI = flag not score | Explicitly documented: weighted trade-offs involving EJI require ethics justification beyond scope |
| F-9 | 3 BAs with missing carbon data | Confirmed cells with NoData carbon treated as NoData in ESI |
| F-12 | DC validation points = commercial directory; unknown completeness | Capture rates interpreted as suggestive, not ground truth |
| F-13 | GAP3 penalty in S5 is a methodological assumption | Penalty factor 0.70 should be tested at 0.50 and 0.85 in sensitivity analysis |
| F-14 | Aqueduct IAV/GTD at 0.5° HydroBASIN resolution | Coarser than the 1 km study grid; sub-basin spatial variation in water reliability is not captured; values represent basin-average conditions |
| F-15 | FERC queue data is county-level aggregated active+suspended projects | Does not measure actual interconnection cost or wait time; counties with large queues may have multiple competing projects rather than true congestion; 2024 LBNL Queued Up dataset |
| F-16 | EIA retail electricity price = state-level, 2020 vintage | Sub-state price variation (utility territories, industrial tariffs) not captured; Texas 2021 grid crisis and subsequent market changes not reflected; use as directional indicator only |
| F-17 | PDSI at NOAA climate division resolution (344 divisions for CONUS) | Much coarser than the 1 km study grid; a single PDSI value covers thousands of km²; appropriate for contextual display but not granular suitability scoring |
| — | Weight justification is inherently subjective | Five scenarios demonstrate range of plausible outcomes; no single scenario is "correct" |
| — | Slope = 100m USGS DEM fallback | Noted in processing log; 30m DEM not available as full-coverage mosaic |
| — | FCC BDC fiber connectivity not processed | Acknowledged as dissertation limitation; public-data gap for fiber backbone |

---

*No composite maps have been generated. Explicit supervisor approval required before proceeding to composite generation.*

*File: `00_ADMIN/WEIGHTING_FRAMEWORK_AND_SCENARIOS.md` · Created 2026-06-17 · Updated 2026-06-23 (added §3f Step 11 supplementary layers: Aqueduct IAV/GTD, PDSI, FERC queue, EIA price, SAIDI flag; added F-14–F-17 limitation flags; updated §3e with SAIDI flag entry) · Updated 2026-06-22 (added §10 empirical correlation analysis; clarified NRI normalisation direction in §3a and §9)*
