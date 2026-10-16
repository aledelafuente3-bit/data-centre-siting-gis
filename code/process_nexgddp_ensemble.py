"""
NEX-GDDP-CMIP6 ensemble heat raster processing.
Input: 100 annual heat-count NetCDF files (5 models × 20 years)
       in 07_climate_heat/processed/annual_heat_counts/
Output:
  - nexgddp_mean_days_gt35_2041_2060.tif  (ensemble mean, days/year)
  - nexgddp_mean_days_gt40_2041_2060.tif  (ensemble mean, days/year)
  - nexgddp_std_days_gt35_2041_2060.tif   (ensemble std dev, uncertainty)
  - nexgddp_std_days_gt40_2041_2060.tif
  All reprojected to EPSG:5070, 1km, study-area extent.
"""

import os, sys, json, glob
os.environ["PROJ_LIB"] = "/Applications/QGIS-LTR.app/Contents/Resources/proj"

import numpy as np
import subprocess
from pathlib import Path

BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
PROC_DIR = f"{BASE}/07_climate_heat/processed/annual_heat_counts"
OUT_DIR  = f"{BASE}/11_processed_layers/rasters"
LOG_FILE = f"{BASE}/00_ADMIN/NEXGDDP_DOWNLOAD_LOG.json"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"

# Study area grid
GRID = dict(xmin=-2295000, ymin=310000, xmax=1791000, ymax=2907000,
            res=1000, cols=4086, rows=2597, epsg=5070)

MODELS = ["ACCESS-CM2", "GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0"]
YEARS  = list(range(2041, 2061))


def gdalwarp_to_grid(src_nc, var_name, out_tif):
    """Reproject NetCDF variable to EPSG:5070 1km grid using gdalwarp."""
    nc_path = f"NETCDF:{src_nc}:{var_name}"
    cmd = [
        f"{GDAL_BIN}/gdalwarp",
        "-t_srs", f"EPSG:{GRID['epsg']}",
        "-te", str(GRID["xmin"]), str(GRID["ymin"]),
               str(GRID["xmax"]), str(GRID["ymax"]),
        "-tr", str(GRID["res"]), str(GRID["res"]),
        "-r", "bilinear",
        "-ot", "Float32",
        "-dstnodata", "-9999",
        "-co", "COMPRESS=LZW",
        "-co", "TILED=YES",
        "-overwrite",
        nc_path, out_tif
    ]
    env = os.environ.copy()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"gdalwarp failed: {r.stderr[:300]}")


def check_completeness():
    """Verify all 100 processed files exist."""
    missing = []
    for model in MODELS:
        for year in YEARS:
            f = f"{PROC_DIR}/heat_counts_{model}_ssp245_{year}.nc"
            if not os.path.exists(f):
                missing.append(f)
    return missing


def main():
    print("NEX-GDDP Ensemble Heat Raster Processing")
    print(f"Expected files: {len(MODELS)} models × {len(YEARS)} years = {len(MODELS)*len(YEARS)}")

    missing = check_completeness()
    if missing:
        print(f"\nERROR: {len(missing)} processed files missing. Aborting.")
        for f in missing:
            print(f"  MISSING: {os.path.basename(f)}")
        sys.exit(1)

    print("All 100 processed files present. Beginning ensemble calculation.")
    print()

    # ─── Step 1: Load all 100 annual heat-count grids ─────────────────────
    # Each file has variables: days_gt35, days_gt40 on a clipped geographic grid
    # First, reproject each to EPSG:5070 1km, then stack

    tmp_dir = "/tmp/nexgddp_reproj"
    os.makedirs(tmp_dir, exist_ok=True)

    # Reproject each annual file to EPSG:5070 1km
    print("Step 1: Reprojecting 100 annual files to EPSG:5070 1km...")
    for i, model in enumerate(MODELS):
        for year in YEARS:
            src = f"{PROC_DIR}/heat_counts_{model}_ssp245_{year}.nc"
            for var in ("days_gt35", "days_gt40"):
                out_tif = f"{tmp_dir}/{var}_{model}_{year}.tif"
                if not os.path.exists(out_tif):
                    gdalwarp_to_grid(src, var, out_tif)
            print(f"  {model} {year}", end="\r", flush=True)
    print("\n  Reprojection complete.")

    # ─── Step 2: Stack and compute ensemble mean/std ───────────────────────
    print("\nStep 2: Computing ensemble mean and std dev...")

    from osgeo import gdal
    gdal.UseExceptions()

    def load_stack(var):
        """Load all 100 reprojected tifs into a 3D array [n, rows, cols]."""
        stack = []
        for model in MODELS:
            for year in YEARS:
                tif = f"{tmp_dir}/{var}_{model}_{year}.tif"
                ds  = gdal.Open(tif)
                arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
                nd  = ds.GetRasterBand(1).GetNoDataValue()
                arr[arr == nd] = np.nan
                stack.append(arr)
                ds = None
        return np.stack(stack, axis=0)  # shape: (100, rows, cols)

    for var in ("days_gt35", "days_gt40"):
        print(f"  Loading {var} stack (100 layers)...")
        stack = load_stack(var)  # (100, 2597, 4086)

        mean_arr = np.nanmean(stack, axis=0).astype(np.float32)
        std_arr  = np.nanstd(stack,  axis=0).astype(np.float32)

        # Replace NaN with -9999
        mean_arr[np.isnan(mean_arr)] = -9999.0
        std_arr[ np.isnan(std_arr)]  = -9999.0

        # Write mean raster
        def write_tif(arr, out_path, nodata=-9999.0):
            # Use a reference tif for CRS/geotransform
            ref_tif = f"{tmp_dir}/{var}_ACCESS-CM2_2041.tif"
            ds_ref  = gdal.Open(ref_tif)
            drv = gdal.GetDriverByName("GTiff")
            ds_out = drv.Create(out_path,
                                GRID["cols"], GRID["rows"], 1, gdal.GDT_Float32,
                                ["COMPRESS=LZW","TILED=YES","BLOCKXSIZE=512","BLOCKYSIZE=512"])
            ds_out.SetGeoTransform(ds_ref.GetGeoTransform())
            ds_out.SetProjection(ds_ref.GetProjection())
            b = ds_out.GetRasterBand(1)
            b.WriteArray(arr)
            b.SetNoDataValue(nodata)
            b.ComputeStatistics(False)
            ds_out.FlushCache()
            ds_ref = None

        out_mean = f"{OUT_DIR}/nexgddp_mean_{var}_2041_2060.tif"
        out_std  = f"{OUT_DIR}/nexgddp_std_{var}_2041_2060.tif"
        write_tif(mean_arr, out_mean)
        write_tif(std_arr,  out_std)
        print(f"  {var}: mean range={mean_arr[mean_arr>-9999].min():.1f}–{mean_arr[mean_arr>-9999].max():.1f}, "
              f"written to {os.path.basename(out_mean)}")

    # ─── Step 3: State-level summary statistics ────────────────────────────
    print("\nStep 3: State-level heat summary statistics...")

    sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')
    from osgeo import ogr

    NAME2ABBR = {
        "Arizona": "AZ", "Illinois": "IL", "Iowa": "IA",
        "Oregon": "OR", "Texas": "TX", "Virginia": "VA", "West Virginia": "WV"
    }
    STATES7 = ["AZ","IL","IA","OR","TX","VA","WV"]

    states_gpkg = f"{BASE}/11_processed_layers/states7_reprojected_EPSG5070.gpkg"
    ds_s  = ogr.Open(states_gpkg)
    lyr_s = ds_s.GetLayer(0)

    ds_m35 = gdal.Open(f"{OUT_DIR}/nexgddp_mean_days_gt35_2041_2060.tif")
    ds_s35 = gdal.Open(f"{OUT_DIR}/nexgddp_std_days_gt35_2041_2060.tif")
    ds_m40 = gdal.Open(f"{OUT_DIR}/nexgddp_mean_days_gt40_2041_2060.tif")

    m35_arr = ds_m35.GetRasterBand(1).ReadAsArray().astype(np.float32)
    s35_arr = ds_s35.GetRasterBand(1).ReadAsArray().astype(np.float32)
    m40_arr = ds_m40.GetRasterBand(1).ReadAsArray().astype(np.float32)
    gt_h    = ds_m35.GetGeoTransform()

    state_heat = {}
    for feat in lyr_s:
        fname = feat.GetField("Name")
        state = NAME2ABBR.get(fname)
        if not state:
            continue
        geom = feat.GetGeometryRef()
        env  = geom.GetEnvelope()

        c0 = max(0, int((env[0] - gt_h[0]) / gt_h[1]))
        c1 = min(GRID["cols"], int((env[1] - gt_h[0]) / gt_h[1]) + 1)
        r0 = max(0, int((gt_h[3] - env[3]) / (-gt_h[5])))
        r1 = min(GRID["rows"], int((gt_h[3] - env[2]) / (-gt_h[5])) + 1)

        mem_drv = gdal.GetDriverByName("MEM")
        mem_ds  = mem_drv.Create("", c1-c0, r1-r0, 1, gdal.GDT_Byte)
        mem_ds.SetGeoTransform([gt_h[0]+c0*gt_h[1], gt_h[1], 0,
                                gt_h[3]+r0*gt_h[5], 0, gt_h[5]])
        mem_ds.SetProjection(ds_m35.GetProjection())
        mem_ds.GetRasterBand(1).Fill(0)

        mem_vec = ogr.GetDriverByName("Memory").CreateDataSource("m")
        ml = mem_vec.CreateLayer("s", srs=lyr_s.GetSpatialRef())
        mf = ogr.Feature(ml.GetLayerDefn())
        mf.SetGeometry(geom.Clone())
        ml.CreateFeature(mf)
        gdal.RasterizeLayer(mem_ds, [1], ml, burn_values=[1])
        mask = mem_ds.GetRasterBand(1).ReadAsArray().astype(bool)
        mem_ds = mem_vec = None

        v35 = m35_arr[r0:r1, c0:c1][mask]
        v35 = v35[v35 > -9999]
        vs35= s35_arr[r0:r1, c0:c1][mask]
        vs35= vs35[vs35 > -9999]
        v40 = m40_arr[r0:r1, c0:c1][mask]
        v40 = v40[v40 > -9999]

        state_heat[state] = {
            "mean_days_gt35":  round(float(v35.mean()), 1) if len(v35) > 0 else None,
            "max_days_gt35":   round(float(v35.max()),  1) if len(v35) > 0 else None,
            "mean_days_gt40":  round(float(v40.mean()), 1) if len(v40) > 0 else None,
            "max_days_gt40":   round(float(v40.max()),  1) if len(v40) > 0 else None,
            "mean_ensemble_std_gt35": round(float(vs35.mean()), 2) if len(vs35) > 0 else None,
        }

    ds_m35 = ds_s35 = ds_m40 = ds_s = None

    print(f"\n{'St':<4} {'Mn>35':>7} {'Mx>35':>7} {'Mn>40':>7} {'Mx>40':>7} {'UncStd':>8}")
    for s in STATES7:
        if s in state_heat:
            h = state_heat[s]
            print(f"{s:<4} "
                  f"{str(h['mean_days_gt35'] or '—'):>7} "
                  f"{str(h['max_days_gt35']  or '—'):>7} "
                  f"{str(h['mean_days_gt40'] or '—'):>7} "
                  f"{str(h['max_days_gt40']  or '—'):>7} "
                  f"{str(h['mean_ensemble_std_gt35'] or '—'):>8}")

    # ─── Step 4: Save log ─────────────────────────────────────────────────
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            log = json.load(f)
    else:
        log = {}
    log["heat_processing"] = {
        "output_files": {
            "mean_gt35": f"{OUT_DIR}/nexgddp_mean_days_gt35_2041_2060.tif",
            "mean_gt40": f"{OUT_DIR}/nexgddp_mean_days_gt40_2041_2060.tif",
            "std_gt35":  f"{OUT_DIR}/nexgddp_std_days_gt35_2041_2060.tif",
            "std_gt40":  f"{OUT_DIR}/nexgddp_std_days_gt40_2041_2060.tif",
        },
        "state_heat_summary": state_heat
    }
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\nLog updated: {LOG_FILE}")
    print("\n══ ENSEMBLE PROCESSING COMPLETE ══")


if __name__ == "__main__":
    main()
