# Suggested captions and provenance

All figures are 300 dpi PNGs. No embedded headline is used; place the numbered caption below the figure in Word.

## Main-text figures

**F01.** Seven-state study area in NAD83 / Conus Albers (EPSG:5070). The inset locates the selected states within the contiguous United States. Source: author’s analysis using US Census TIGER/Line 2025 state boundaries.

**F02.** Sequential hard exclusions and retained analytical cells. Each excluded cell is assigned to the first applicable rule, so categories do not double-count overlaps. Source: author’s analysis of PAD-US 4.1, FEMA NFHL and Annual NLCD data.

**F03.** Baseline three-pillar GRIC scores across viable cells. The colour scale covers the observed raster range; grey cells were excluded or contain NoData. Scores express relative modelled suitability under the baseline criteria and weights. Source: author’s analysis using the datasets specified in Chapter 3.

**F04.** Environmental Site Index, proximity-based Operational Feasibility Index and Sustainability Impact Index on a common 0–1 scale. The vertically aligned panels preserve legibility at dissertation text width. Grey cells were excluded or contain NoData. Source: author’s analysis using the datasets specified in Chapter 3.

**F05.** Distribution of polygon-clipped GRIC scores by state. Boxes show the interquartile range, horizontal lines show medians, diamonds show means and whiskers extend from the 5th to the 95th percentile. The dashed line indicates the study-area median. Source: author’s analysis of the final three-pillar GRIC raster.

**F06.** Pillar relationships and quartile-defined spatial trade-offs. Correlations use all 1,253,067 viable cells; trade-off categories identify cells in the relevant upper and lower pillar quartiles. Source: author’s analysis of the final pillar rasters.

**F07.** Baseline and CRITIC-derived criterion weights within each pillar. CRITIC weights reflect both spatial variation and correlation conflict; pillar weights remain equal at one third. Source: author’s analysis following Diakoulaki, Mavrotas and Papayannakis (1995).

**F08.** Agreement between the baseline and CRITIC-weighted models under global ranking and upper-decile definitions. Source: author’s analysis of the final three-pillar criterion rasters.

**F09.** Spearman rank stability under alternative weighting assumptions. Points show median correlations, thick intervals show the 5th–95th percentile and short marks show the minimum across 1,000 draws. Source: author’s analysis of a fixed 50,000-cell sample; seed 42.

**F10.** External spatial concordance between observed facility locations and GRIC scores. Capture rates use thresholds derived from all viable cells; score summaries compare 1,168 facilities with valid GRIC values and 5,000 randomly sampled viable cells. The Mann–Whitney comparison yielded U = 3,175,525, z = −4.663, p = 3.11 × 10⁻⁶ and rank-biserial r = 0.088. Source: author’s analysis.

## Appendix figures

**A01.** Grid-carbon suitability based on EPA eGRID 2023 balancing-authority annual CO₂e total output-emission rates. Scores use p5–p95 inversion across study-area balancing authorities: `clip((447.9 − rate) / 345.7, 0, 1)`, with rate in lb CO₂e/MWh. White lines show balancing-authority boundaries. Source: author’s analysis of EPA eGRID 2023 Revision 2.

**A02.** Baseline and projected water-stress suitability and the change between them. Panel (a) uses the Aqueduct 4.0 baseline; panel (b) uses the 2050 business-as-usual projection; panel (c) maps the projected score minus the baseline score. Negative values therefore indicate increasing projected water stress. The change display is clipped at ±0.20 to reveal the predominant spatial variation; more extreme values use the end colours. Source: author’s analysis of WRI Aqueduct 4.0.

**A03.** Proximity to internet exchange locations accessed through PeeringDB. Faint surrounding-state boundaries provide geographic context. Some exchanges outside the seven study states are retained because they contribute to nearest-distance calculations; scores reach zero at distances of 500 km or more. Source: author’s analysis of PeeringDB records accessed 16 July 2026.

**A04.** Lower-burden suitability based on the community-level Environmental Justice Index. The mapped criterion is `1 − RPL_EJI`, so higher scores indicate lower existing environmental burden. Source: author’s analysis of CDC/ATSDR EJI 2024.

## Retired graphics

- The former state choropleth is retired because it used rectangular-extent means.
- The former carbon figure is retired because it documented a superseded subregional/1,800-unit transformation.
- The former facility-overlay map is retired because the archived point-score CSV does not reproduce the final 1,168-facility validation sample exactly.
- The former `GRIC ≥ 0.70` map is retired because 0.70 is not the study-wide p90 threshold and “high suitability” implies an unsupported absolute classification.
