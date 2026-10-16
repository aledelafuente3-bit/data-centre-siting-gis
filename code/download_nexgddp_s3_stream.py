"""
NEX-GDDP-CMIP6 S3 stream-process download script.
Strategy: download each annual file to /tmp, clip to study bbox,
compute heat-day counts, record MD5, delete raw file.
Processed arrays saved as small NetCDF subsets (~0.1 MB each).

Disk usage: ~250 MB peak (one raw file at a time), plus growing processed outputs.
"""

import os, sys, hashlib, subprocess, json, time
from datetime import datetime

os.environ["PROJ_LIB"] = "/Applications/QGIS-LTR.app/Contents/Resources/proj"

import numpy as np
import xarray as xr

BASE   = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RAW_DIR   = f"{BASE}/07_climate_heat/raw/nexgddp_cmip6"       # pilot files live here
PROC_DIR  = f"{BASE}/07_climate_heat/processed/annual_heat_counts"
LOG_FILE  = f"{BASE}/00_ADMIN/NEXGDDP_DOWNLOAD_LOG.json"

S3_BASE = "https://nex-gddp-cmip6.s3.us-west-2.amazonaws.com/NEX-GDDP-CMIP6"

# Study area bbox (geographic WGS84)
LON_MIN, LON_MAX = -124.57, -75.24
LAT_MIN, LAT_MAX = 25.84,  46.24

MODELS = {
    "ACCESS-CM2":    ("r1i1p1f1", "gn"),
    "GFDL-ESM4":     ("r1i1p1f1", "gr1"),
    "IPSL-CM6A-LR":  ("r1i1p1f1", "gr"),
    "MPI-ESM1-2-HR": ("r1i1p1f1", "gn"),
    "MRI-ESM2-0":    ("r1i1p1f1", "gn"),
}
YEARS = list(range(2041, 2061))


def nc_filename(model, realm, grid, year):
    return f"tasmax_day_{model}_ssp245_{realm}_{grid}_{year}.nc"

def s3_url(model, realm, grid, year):
    fname = nc_filename(model, realm, grid, year)
    return f"{S3_BASE}/{model}/ssp245/{realm}/tasmax/{fname}"

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def is_valid_nc(path):
    if not os.path.exists(path) or os.path.getsize(path) < 10240:
        return False
    with open(path, "rb") as f:
        magic = f.read(4)
    return magic[:3] in (b'\x89HD', b'CDF') or magic[:4] == b'\x89HDF'

def processed_path(model, year):
    return f"{PROC_DIR}/heat_counts_{model}_ssp245_{year}.nc"

def process_file(raw_path, model, year):
    """
    Open NetCDF, clip to study bbox, compute days >35°C and >40°C.
    Returns xarray Dataset with two variables (days_gt35, days_gt40).
    """
    # decode_times=False: avoids cftime requirement for non-standard calendars
    # (e.g. GFDL-ESM4 uses 365_day calendar). We only count day exceedances,
    # so the actual time values are not needed.
    ds = xr.open_dataset(raw_path, engine='h5netcdf', decode_times=False)

    # Some models store lon as 0–360; convert if needed
    if float(ds['lon'].max()) > 180:
        ds = ds.assign_coords(lon=(((ds.lon + 180) % 360) - 180))
        ds = ds.sortby('lon')

    ds = ds.sel(
        lat=slice(LAT_MIN - 0.5, LAT_MAX + 0.5),
        lon=slice(LON_MIN - 0.5, LON_MAX + 0.5)
    )

    tasmax_c = ds['tasmax'] - 273.15
    days_gt35 = (tasmax_c > 35).sum(dim='time').astype(np.int16)
    days_gt40 = (tasmax_c > 40).sum(dim='time').astype(np.int16)

    result = xr.Dataset({
        'days_gt35': days_gt35,
        'days_gt40': days_gt40,
    })
    result.attrs['model']  = model
    result.attrs['year']   = year
    result.attrs['source'] = 'NEX-GDDP-CMIP6 v1.0'
    result.attrs['scenario'] = 'ssp245'
    result.attrs['variable'] = 'tasmax'

    ds.close()
    return result


def main():
    os.makedirs(PROC_DIR, exist_ok=True)

    # Load existing log if any
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            log = json.load(f)
    else:
        log = {}

    log.update({
        "download_date": datetime.now().isoformat(),
        "dataset": "NASA NEX-GDDP-CMIP6 v1.0",
        "variable": "tasmax",
        "scenario": "SSP2-4.5",
        "period": "2041-2060",
        "models": list(MODELS.keys()),
        "model_grid_labels": {m: g for m, (r, g) in MODELS.items()},
        "total_expected": 100,
        "method": "S3 stream-process (THREDDS unavailable)",
        "files": log.get("files", {})
    })

    print(f"[{datetime.now():%H:%M:%S}] NEX-GDDP S3 stream-process starting")
    print(f"Processing directory: {PROC_DIR}")

    # Build manifest
    manifest = []
    for model, (realm, grid) in MODELS.items():
        for year in YEARS:
            proc_path = processed_path(model, year)
            raw_in_place = os.path.join(RAW_DIR, nc_filename(model, realm, grid, year))
            manifest.append((model, realm, grid, year, raw_in_place, proc_path))

    already_processed = [m for m in manifest if os.path.exists(m[5])]
    to_process_inplace = [m for m in manifest
                          if not os.path.exists(m[5]) and os.path.exists(m[4])]
    to_download = [m for m in manifest
                   if not os.path.exists(m[5]) and not os.path.exists(m[4])]

    print(f"Already processed: {len(already_processed)}")
    print(f"Raw in place (pilot files): {len(to_process_inplace)}")
    print(f"Needs download: {len(to_download)}")
    print()

    failed = []
    processed = 0

    # --- Process already-downloaded raw files (9 pilot files) ---
    for model, realm, grid, year, raw_path, proc_path in to_process_inplace:
        fname = os.path.basename(raw_path)
        print(f"[pilot] Processing {fname} ...", flush=True)
        try:
            result = process_file(raw_path, model, year)
            result.to_netcdf(proc_path)
            fsize = os.path.getsize(raw_path)
            cksum = md5_file(raw_path)
            log["files"][fname] = {
                "status": "processed_from_pilot",
                "raw_size_bytes": fsize,
                "md5": cksum,
                "processed_path": proc_path
            }
            processed += 1
            print(f"  OK → {os.path.basename(proc_path)}")
        except Exception as e:
            failed.append(fname)
            log["files"][fname] = {"status": "failed_processing", "error": str(e)}
            print(f"  FAILED: {e}")

    # --- Download + process new files ---
    for i, (model, realm, grid, year, raw_path, proc_path) in enumerate(to_download, 1):
        fname   = nc_filename(model, realm, grid, year)
        tmp_raw = f"/tmp/nexgddp_tmp_{model}_{year}.nc"
        url     = s3_url(model, realm, grid, year)

        print(f"[{i}/{len(to_download)}] {fname} ...", flush=True)
        t0 = time.time()

        # Download to /tmp
        if os.path.exists(tmp_raw):
            os.remove(tmp_raw)
        r = subprocess.run(
            ["curl", "-fsSL", "--retry", "3", "--retry-delay", "5",
             "--connect-timeout", "30", "--max-time", "600",
             "-o", tmp_raw, url],
            capture_output=True, text=True
        )

        if r.returncode != 0 or not is_valid_nc(tmp_raw):
            err = r.stderr.strip() if r.returncode != 0 else "invalid_nc_magic"
            failed.append(fname)
            log["files"][fname] = {"status": "download_failed", "error": err, "url": url}
            print(f"  FAILED download: {err}")
            if os.path.exists(tmp_raw):
                os.remove(tmp_raw)
            # Write log and PAUSE
            with open(LOG_FILE, "w") as f:
                json.dump(log, f, indent=2)
            print(f"\nPAUSING — {fname} failed to download. Fix before continuing.")
            print(f"URL attempted: {url}")
            sys.exit(1)

        dl_time = time.time() - t0
        fsize   = os.path.getsize(tmp_raw)
        cksum   = md5_file(tmp_raw)
        print(f"  Downloaded {fsize/1e6:.1f} MB in {dl_time:.1f}s  md5={cksum[:8]}...")

        # Process (clip + heat-day counts)
        try:
            result = process_file(tmp_raw, model, year)
            result.to_netcdf(proc_path)
            proc_time = time.time() - t0 - dl_time
            print(f"  Processed in {proc_time:.1f}s → {os.path.basename(proc_path)}")
        except Exception as e:
            failed.append(fname)
            log["files"][fname] = {"status": "processing_failed", "error": str(e),
                                   "raw_size_bytes": fsize, "md5": cksum}
            print(f"  FAILED processing: {e}")
            os.remove(tmp_raw)
            with open(LOG_FILE, "w") as f:
                json.dump(log, f, indent=2)
            sys.exit(1)

        # Record and delete raw
        log["files"][fname] = {
            "status": "downloaded_and_processed",
            "raw_size_bytes": fsize,
            "md5": cksum,
            "download_time_s": round(dl_time, 1),
            "url": url,
            "processed_path": proc_path
        }
        os.remove(tmp_raw)
        processed += 1

        # Flush log after every file
        with open(LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)

    # Summary
    total_valid = len(already_processed) + processed
    log["total_processed"] = total_valid
    log["total_failed"] = len(failed)
    log["final_status"] = "complete" if not failed and total_valid == 100 else "incomplete"

    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Done: {datetime.now():%H:%M:%S}")
    print(f"Total processed: {total_valid}/100")
    if failed:
        print(f"Failed: {len(failed)}")
        for f in failed:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("All 100 files processed. Ensemble complete.")

if __name__ == "__main__":
    main()
