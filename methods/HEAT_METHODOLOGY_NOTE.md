# Heat Exposure Criterion — Methodology Note
**Date:** 2026-06-01  
**Status:** Candidate layer — approved for QC review only; not yet in scored MCDA composite.

---

## 1. Dataset

**NASA NEX-GDDP-CMIP6 v1.0**  
Thrasher, B., W. Wang, A. Tawfik, F. Sun, R. Tang, M. Corneau-Souriau, M. Maurer, N. Jain, D. Bader, and P. Bhaskaran, 2022: *NASA Global Daily Downscaled Projections, CMIP6.* Scientific Data, 9, 262. https://doi.org/10.1038/s41597-022-01393-4  
Source: `s3://nex-gddp-cmip6/` (AWS Open Data, public HTTPS access)

---

## 2. Model ensemble

Five CMIP6 models were selected, covering a range of modelling centres and climate sensitivities:

| Model | Institution | Grid label | Calendar |
|-------|------------|------------|----------|
| ACCESS-CM2 | CSIRO/ARCCSS (Australia) | gn | standard |
| GFDL-ESM4 | NOAA-GFDL (USA) | gr1 | **365_day (non-standard)** |
| IPSL-CM6A-LR | IPSL (France) | gr | standard |
| MPI-ESM1-2-HR | MPI-M (Germany) | gn | standard |
| MRI-ESM2-0 | MRI (Japan) | gn | standard |

**GFDL-ESM4 calendar note:** GFDL-ESM4 uses a 365-day non-standard calendar. `xarray.open_dataset(decode_times=False)` was applied to all files to avoid cftime calendar errors. Only day-count exceedances are computed; calendar differences do not affect results.

---

## 3. Scenario and period

- **Scenario:** SSP2-4.5 (Shared Socioeconomic Pathway 2 — intermediate emissions pathway)
- **Period:** 2041–2060 (20 years, 100 model-years total)
- **Variable:** `tasmax` — daily maximum near-surface air temperature (K)

---

## 4. Download and processing

**Method:** Stream-process approach (disk-space constraint — ~244 MB raw file per model-year; ~16 GB free disk):
1. Download one raw file to `/tmp` (~244 MB)
2. Convert from K to °C: `tasmax_C = tasmax − 273.15`
3. Clip to study-area bounding box: lon −124.88°–−74.88°, lat 25.38°–46.62° (0.5° buffer beyond study area)
4. Count annual exceedance days: `days_gt35 = (tasmax_C > 35).sum(dim='time')`, `days_gt40 = (tasmax_C > 40).sum(dim='time')`
5. Save processed annual counts (~70 KB NetCDF) to `07_climate_heat/processed/annual_heat_counts/`
6. Record MD5 checksum of raw file
7. Delete raw file from `/tmp`

**Files processed:** 100/100 (0 failures)  
**Pilot files (pre-existing raw files):** 9 (ACCESS-CM2, MPI-ESM1-2-HR, MRI-ESM2-0 for 2041, 2050, 2060)  
**New files downloaded via S3:** 91  
**MD5 checksums:** Recorded per-file in `00_ADMIN/NEXGDDP_DOWNLOAD_LOG.json`

---

## 5. Original spatial resolution

**0.25° × 0.25°** (~27 km at mid-latitudes) on a regular geographic lat/lon grid (WGS84).

> **Resolution caveat — CRITICAL:** The 1 km MCDA grid alignment does **not** create 1 km climate-model detail. The native NEX-GDDP-CMIP6 resolution is 0.25° (~27 km). Each 27 km source cell is interpolated to ~729 1km MCDA cells during reprojection. The resulting 1 km rasters represent spatially smooth patterns at the 0.25° scale; no sub-0.25° climate information is present. This must be stated explicitly in any methodological description. The rasters are appropriate for regional siting comparisons at the state or county level, not for site-level micro-climate analysis.

---

## 6. Ensemble averaging

- All 100 annual grids (5 models × 20 years) were stacked to shape **(100, 86, 201)** per variable
- **Ensemble mean:** `np.mean(stack, axis=0)` → single mean grid (86×201)
- **Ensemble standard deviation:** `np.std(stack, axis=0)` → single uncertainty grid (86×201)
- Averaging is unweighted across model-years: each of the 100 layers (model-year combinations) contributes equally
- No missing data in the processed annual grids; NoData handling was not required for the ensemble computation

---

## 7. Reprojection

**Intermediate step:** Each ensemble output was written as a WGS84 NetCDF, then converted to a georeferenced GeoTIFF using `gdal_translate -a_srs EPSG:4326 -a_ullr [extent]`.

**Final reprojection:**
- Tool: `gdalwarp` (QGIS 3.34 GDAL 3.3)
- Source CRS: EPSG:4326 (WGS84 geographic)
- Target CRS: EPSG:5070 (NAD83 / Conus Albers)
- Target extent: xmin=−2295000, ymin=310000, xmax=1791000, ymax=2907000 (metres, EPSG:5070)
- Target resolution: **1000 m × 1000 m**
- **Resampling method: bilinear interpolation**
- NoData: −9999 (source: none; only study-extent ocean/boundary cells are NoData in output)

---

## 8. Output rasters (all EPSG:5070, 1 km, 4086×2597)

| File | Description | Role | Min | Max | Mean | Valid% |
|------|-------------|------|-----|-----|------|--------|
| `nexgddp_mean_days_gt35_2041_2060.tif` | Ensemble mean annual days with tasmax >35°C | **MAIN CRITERION** | 0.0 | 226.7 | 35.5 | 91.33% |
| `nexgddp_mean_days_gt40_2041_2060.tif` | Ensemble mean annual days with tasmax >40°C | Sensitivity | 0.0 | 124.7 | 6.8 | 91.33% |
| `nexgddp_std_days_gt35_2041_2060.tif` | Ensemble std dev, days >35°C | Uncertainty/context | 0.0 | 27.0 | 11.6 | 91.33% |
| `nexgddp_std_days_gt40_2041_2060.tif` | Ensemble std dev, days >40°C | Uncertainty/context | 0.0 | 24.0 | 5.0 | 91.33% |

**Valid% note:** 91.33% valid pixels for all four outputs. The 8.67% NoData corresponds to offshore and out-of-CONUS cells within the EPSG:5070 bounding box extent. All seven study-state land areas are fully covered.

---

## 9. Seven-state coverage (ensemble mean, SSP2-4.5, 2041–2060)

| State | Mean days >35°C | Max days >35°C | Mean days >40°C | Max days >40°C |
|-------|:--------------:|:--------------:|:--------------:|:--------------:|
| AZ | 89.8 | 184.7 | 35.0 | 124.7 |
| TX | 77.7 | 165.3 | 16.6 | 88.9 |
| IL | 25.2 | 51.0 | 2.1 | 5.9 |
| IA | 20.4 | 42.0 | 1.2 | 4.8 |
| VA | 19.0 | 37.2 | 2.1 | 5.8 |
| WV | 15.3 | 36.9 | 1.7 | 5.8 |
| OR | 14.9 | 61.0 | 1.5 | 16.5 |

*Values derived from WGS84 arrays using state bounding-box masks.*

---

## 10. Integrity check

All 100 processed NetCDF files were validated:
- Each file confirmed to have variables `days_gt35` and `days_gt40` of type int16
- Grid confirmed identical across all 5 models: 86 lat × 201 lon, 0.25° resolution
- Value ranges confirmed physically plausible (e.g., ACCESS-CM2 days_gt35: 0–257; GFDL-ESM4: 0–189)
- MD5 checksums recorded for all 100 raw source files in `NEXGDDP_DOWNLOAD_LOG.json`

---

## 11. Retained uncertainty layers

- `nexgddp_std_days_gt35_2041_2060.tif` — mean ensemble std dev 11.6 days/yr, max 27.0 days/yr
- `nexgddp_std_days_gt40_2041_2060.tif` — mean ensemble std dev 5.0 days/yr, max 24.0 days/yr

The std rasters provide a spatially explicit uncertainty map. Cells with high std (>20 days/yr) indicate strong model disagreement and should be interpreted cautiously. These layers are available for optional MCDA sensitivity analysis.

---

## 12. MCDA integration status

**Status: CANDIDATE LAYER — QC / review only.**  
Per supervisor instruction, the heat rasters have been added to the QGIS working project under `QC / Candidate Layers — Climate Heat`. They are not included in the scored MCDA composite until review is complete and weights are approved.
