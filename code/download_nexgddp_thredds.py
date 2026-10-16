"""
NEX-GDDP-CMIP6 THREDDS NCSS spatial-subset download script
Dataset: NASA NEX-GDDP-CMIP6 v1.0 (Thrasher et al. 2022)
Variable: tasmax (daily max near-surface air temperature)
Scenario: SSP2-4.5
Period: 2041-2060
Study area bbox: lon -124.57 to -75.24, lat 25.84 to 46.24
"""

import os
import hashlib
import subprocess
import sys
import time
import json
from datetime import datetime

BASE_DIR = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RAW_DIR  = f"{BASE_DIR}/07_climate_heat/raw/nexgddp_cmip6"
LOG_FILE = f"{BASE_DIR}/00_ADMIN/NEXGDDP_DOWNLOAD_LOG.json"

THREDDS_BASE = "https://ds.nccs.nasa.gov/thredds/ncss/grid/CMIP/NASA/NEX/GDDP/CMIP6"

BBOX = dict(north=46.24, west=-124.57, east=-75.24, south=25.84)

# Model registry: model → (realm, grid_label)
MODELS = {
    "ACCESS-CM2":    ("r1i1p1f1", "gn"),
    "GFDL-ESM4":     ("r1i1p1f1", "gr1"),
    "IPSL-CM6A-LR":  ("r1i1p1f1", "gr"),
    "MPI-ESM1-2-HR": ("r1i1p1f1", "gn"),
    "MRI-ESM2-0":    ("r1i1p1f1", "gn"),
}

YEARS = list(range(2041, 2061))  # 2041-2060 inclusive


def expected_filename(model, realm, grid, year):
    return f"tasmax_day_{model}_ssp245_{realm}_{grid}_{year}.nc"


def thredds_url(model, realm, grid, year):
    fname = expected_filename(model, realm, grid, year)
    params = (
        f"var=tasmax"
        f"&north={BBOX['north']}&west={BBOX['west']}&east={BBOX['east']}&south={BBOX['south']}"
        f"&horizStride=1"
        f"&time_start={year}-01-01T00:00:00Z&time_end={year}-12-31T00:00:00Z"
        f"&accept=netCDF4"
    )
    path = f"{THREDDS_BASE}/{model}/ssp245/{realm}/tasmax/{fname}"
    return f"{path}?{params}"


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid_nc(path):
    """Return True if file is a valid NetCDF (not an HTML error page)."""
    if not os.path.exists(path) or os.path.getsize(path) < 1024:
        return False
    with open(path, "rb") as f:
        magic = f.read(4)
    # NetCDF4/HDF5 magic: \x89HDF
    # NetCDF classic magic: CDF\x01 or CDF\x02
    return magic[:4] in (b'\x89HDF', b'CDF\x01', b'CDF\x02') or magic[:3] == b'\x89HD'


def build_manifest():
    """Return list of (model, realm, grid, year, filepath) for all 100 expected files."""
    manifest = []
    for model, (realm, grid) in MODELS.items():
        for year in YEARS:
            fname = expected_filename(model, realm, grid, year)
            fpath = os.path.join(RAW_DIR, fname)
            manifest.append((model, realm, grid, year, fpath))
    return manifest


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    manifest = build_manifest()

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] NEX-GDDP THREDDS download starting")
    print(f"Expected files: {len(manifest)} (5 models × 20 years)")

    # Categorise: already exists (and valid), needs download, already exists but invalid
    existing_valid   = []
    existing_invalid = []
    to_download      = []

    for model, realm, grid, year, fpath in manifest:
        if os.path.exists(fpath):
            if is_valid_nc(fpath):
                existing_valid.append((model, year, fpath))
            else:
                existing_invalid.append((model, year, fpath))
                to_download.append((model, realm, grid, year, fpath))
        else:
            to_download.append((model, realm, grid, year, fpath))

    print(f"Already valid:  {len(existing_valid)}")
    print(f"Invalid/corrupt: {len(existing_invalid)}")
    print(f"To download:    {len(to_download)}")
    print()

    if existing_invalid:
        print("WARNING: These files exist but failed NetCDF validity check — will re-download:")
        for m, y, p in existing_invalid:
            print(f"  {os.path.basename(p)}")
        print()

    log = {
        "download_date": datetime.now().isoformat(),
        "dataset": "NASA NEX-GDDP-CMIP6 v1.0",
        "variable": "tasmax",
        "scenario": "SSP2-4.5",
        "period": "2041-2060",
        "models": list(MODELS.keys()),
        "total_expected": len(manifest),
        "pre_existing_valid": len(existing_valid),
        "downloaded": 0,
        "failed": 0,
        "files": {}
    }

    # Log pre-existing valid files
    for model, year, fpath in existing_valid:
        key = os.path.basename(fpath)
        log["files"][key] = {
            "status": "pre_existing",
            "size_bytes": os.path.getsize(fpath),
            "md5": md5(fpath)
        }
        print(f"  [pre-existing] {key}  md5={log['files'][key]['md5'][:8]}...")

    # Download new/invalid files
    failed = []
    downloaded = 0

    for i, (model, realm, grid, year, fpath) in enumerate(to_download, 1):
        fname = os.path.basename(fpath)
        url   = thredds_url(model, realm, grid, year)

        print(f"[{i}/{len(to_download)}] Downloading {fname} ...", flush=True)
        t0 = time.time()

        # Remove invalid file if it exists
        if os.path.exists(fpath):
            os.remove(fpath)

        result = subprocess.run(
            ["curl", "-fsSL", "--retry", "3", "--retry-delay", "5",
             "--connect-timeout", "30", "--max-time", "300",
             "-o", fpath, url],
            capture_output=True, text=True
        )

        elapsed = time.time() - t0

        if result.returncode != 0 or not is_valid_nc(fpath):
            status = "FAILED"
            detail = result.stderr.strip() if result.returncode != 0 else "invalid_nc_magic"
            failed.append(fname)
            log["failed"] += 1
            log["files"][fname] = {"status": "failed", "error": detail, "url": url}
            print(f"  FAILED: {detail}")
            # Remove bad file
            if os.path.exists(fpath):
                os.remove(fpath)
        else:
            size  = os.path.getsize(fpath)
            cksum = md5(fpath)
            downloaded += 1
            log["downloaded"] += 1
            log["files"][fname] = {
                "status": "downloaded",
                "size_bytes": size,
                "md5": cksum,
                "elapsed_s": round(elapsed, 1),
                "url": url
            }
            print(f"  OK  {size/1e6:.1f} MB  {elapsed:.1f}s  md5={cksum[:8]}...")

        # Flush log after every file
        with open(LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)

    # Final summary
    print()
    print("=" * 60)
    print(f"Download complete: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"Pre-existing valid: {len(existing_valid)}")
    print(f"Newly downloaded:   {downloaded}")
    print(f"Failed:             {len(failed)}")

    if failed:
        print()
        print("FAILED FILES (download manually or fall back to S3):")
        for f in failed:
            print(f"  {f}")
        sys.exit(1)
    else:
        total_valid = len(existing_valid) + downloaded
        if total_valid == len(manifest):
            print(f"\nALL {len(manifest)} files present and valid. Ensemble complete.")
        else:
            missing = len(manifest) - total_valid
            print(f"\nWARNING: {missing} files missing. Do not proceed with incomplete ensemble.")
            sys.exit(1)

    # Final log update
    log["final_status"] = "complete" if not failed else "incomplete"
    log["total_valid_files"] = len(existing_valid) + downloaded
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)
    print(f"\nLog written to: {LOG_FILE}")


if __name__ == "__main__":
    main()
