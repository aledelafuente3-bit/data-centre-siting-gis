# Validation Summary — Data Centre Siting Model

**Generated:** 2026-06-15  
**Method:** Spatial score extraction + constrained random comparison  
**Status:** Pre-weighting validation (no composite MCDA score exists yet; individual criterion layers only)

---

## 1. Dataset

**Validation points:** Commercial data centre directory (Datacenter Hawk/CBRE format — unconfirmed exact source). See `DATA_CENTER_VALIDATION_PROVENANCE.md` for full provenance.  
**This dataset is NOT from OpenStreetMap.**

| Statistic | Value |
|-----------|-------|
| Input records | 1,598 |
| Valid points in 7-state mask | 1,575 |
| Points outside mask (skipped) | 23 |

**State breakdown (valid points):**

| State | DC points | % of total |
|-------|-----------|-----------|
| VA | 615 | 39.0% |
| TX | 450 | 28.6% |
| IL | 246 | 15.6% |
| AZ | 171 | 10.9% |
| OR | 93 | 5.9% |
| IA | 0 | 0.0% |
| WV | 0 | 0.0% |

**Comparison baseline:** 5,000 constrained random eligible points (pct_waterwetland ≤ 50%, pct_eligible ≥ 10%), drawn uniformly from valid mask cells. Random seed = 42.

---

## 2. 230kV Transmission Proximity — Capture Rates

This is the primary grid-access criterion (M2 OFI). Lower proximity = closer to high-voltage infrastructure = higher suitability.

| Threshold | Distance cutoff | DC validation points captured | Random baseline |
|-----------|----------------|-------------------------------|-----------------|
| Top 10% of cells | ≤ 2,236 m | **59.9%** | ~10% |
| Top 20% of cells | ≤ 5,000 m | **77.8%** | ~20% |
| Top 30% of cells | ≤ 8,246 m | **87.0%** | ~30% |

**Interpretation:** The 230kV proximity layer shows very strong spatial signal. Known data centres cluster overwhelmingly near high-voltage transmission infrastructure — approximately 6× enrichment at the top 10% threshold relative to random. This provides strong pre-weighting validation that the layer captures real siting behaviour.

**Mean 230kV proximity at validation points vs. random:**

| Dataset | Mean proximity | n |
|---------|---------------|---|
| DC validation points | 4,011 m | 1,575 |
| Random eligible cells | 28,126 m | 5,000 |
| **Ratio (DC / random)** | **0.143** | — |

DC facilities are located, on average, 7× closer to 230kV lines than random eligible land.

**Per-state mean 230kV proximity at DC points:**

| State | Mean proximity (m) | n |
|-------|-------------------|---|
| VA | 2,382 | 615 |
| IL | 2,826 | 246 |
| AZ | 3,645 | 171 |
| TX | 6,453 | 450 |
| OR | 6,766 | 93 |

Northern Virginia's extreme data centre density near PJM 230kV infrastructure is reflected in the lowest mean proximity (2,382 m).

---

## 3. Environmental Suitability Criterion Comparisons

| Criterion | DC mean | Random mean | DC/Random | Direction |
|-----------|---------|-------------|-----------|-----------|
| `carbon_suit` (0–1, higher=better) | 0.362 | 0.380 | 0.95 | Slightly lower |
| `water_suit` (0–1, higher=better) | 0.478 | 0.472 | 1.01 | Essentially equal |
| `wildfire_score` (0–100, lower=better) | 57.5 | 67.3 | 0.85 | **Better (lower risk)** |
| `flood_score` (0–100, lower=better) | 86.7 | 55.9 | 1.55 | **Worse (higher risk)** |

**Key findings:**

- **Carbon suitability:** DC locations show marginally lower carbon suitability than random — consistent with the pattern that historically fossil-fuel-intensive BAs (PJM, ERCOT gas zones) host many data centres. This underscores why carbon is an important criterion for sustainable siting.
- **Water stress:** Near-identical distribution between DC locations and random eligible land — water stress does not strongly predict current siting behaviour. This may reflect that water stress was not historically a decision factor.
- **Wildfire:** DC locations have meaningfully lower wildfire risk scores (57.5 vs 67.3) — consistent with data centres avoiding fire-prone rural/wildland areas and concentrating in urban/suburban settings.
- **Inland flood:** DC locations show *higher* NRI flood scores (86.7 vs 55.9). This is a notable finding — existing facilities appear to be located in higher flood-risk cells. Possible explanations: proximity to rivers (cooling water access), urban river corridors, or the fact that historical siting did not weight flood risk. This reinforces the importance of the NFHL exclusion layer.

---

## 4. Validation Interpretation

**What the validation demonstrates:**

The 230kV proximity layer shows strong spatial association with known facility locations — the strongest signal of any individual criterion tested. This is consistent with the hypothesis that grid access is the dominant operational siting factor for data centres.

Environmental suitability (ESI) criteria show weaker or mixed association with existing facilities. This is expected: the ESI module is designed to identify locations *better* than where industry has historically sited, not to replicate existing patterns. The divergence in carbon and flood scores between existing DCs and the model's preferred locations reflects the dissertation's core argument — that sustainable siting requires deliberate departure from historical patterns.

**What the validation cannot demonstrate:**

- Completeness: IA and WV have no validation points; validation is effectively limited to VA, TX, IL, AZ, OR.
- Whether "top cells" in the eventual composite MCDA map capture a proportionally higher share of facilities — this cannot be assessed until weights are assigned and composite maps produced.

---

## 5. Limitations

1. **Dataset bias:** Commercial directory over-represents Northern Virginia and co-location operators; underrepresents rural and government facilities.
2. **IA and WV gap:** Two of the seven study-area states have zero validation points.
3. **Geocoding uncertainty:** ±100 m positional error may misplace some points across cell boundaries at 1 km resolution.
4. **No composite score:** This validation assesses individual layers only. True model validation requires composite ESI/OFI scores (deferred pending weight approval).
5. **Temporal mismatch:** Unknown directory compilation date; some criterion layers use 2024 data.

---

## 6. Output Files

| File | Description |
|------|-------------|
| `observed_data_center_points/data_centers_7state_EPSG5070.gpkg` | 1,575 valid DC points, EPSG:5070 |
| `constrained_random_points/random_eligible_5000_EPSG5070.gpkg` | 5,000 random eligible comparison points |
| `extracted_scores/data_center_scores.csv` | Raster scores at all 1,575 DC points |
| `extracted_scores/random_scores.csv` | Raster scores at all 5,000 random points |
| `DATA_CENTER_VALIDATION_PROVENANCE.md` | Full source documentation |
