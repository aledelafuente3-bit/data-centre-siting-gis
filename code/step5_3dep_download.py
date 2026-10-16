#!/usr/bin/env python3
"""
Step 5a: Download USGS 3DEP 1 arc-second DEM tiles for 7-state study area.
Tiles: s3://prd-tnm/StagedProducts/Elevation/1/TIFF/current/n{LAT}w{LON}/USGS_1_n{LAT}w{LON}.tif
Naming: n36w076 = tile covering lat 36-37N, lon 75-76W (note: 1 degree square, SW corner)
"""
import os, subprocess, itertools

OUT_DIR = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/08_protected_areas_and_land_cover/raw/dem_3dep"
os.makedirs(OUT_DIR, exist_ok=True)

S3_BASE = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/current"

# State bounding boxes (lat_min, lat_max, lon_min, lon_max in positive degrees West)
# Using 0.5° buffer to ensure full coverage at state edges
STATES = {
    'AZ': (31, 37, 109, 115),
    'IL': (36, 43, 87,  92),
    'IA': (40, 44, 90,  97),
    'OR': (41, 47, 116, 125),
    'TX': (25, 37, 93,  107),
    'VA': (36, 40, 75,  84),
    'WV': (37, 41, 77,  83),
}

# Build set of all tiles needed
tiles = set()
for state, (lat_min, lat_max, lon_min, lon_max) in STATES.items():
    for lat in range(lat_min, lat_max + 1):
        for lon in range(lon_min, lon_max + 1):
            tiles.add((lat, lon))

print(f"Total unique 1°×1° tiles needed: {len(tiles)}")

# Check which tiles exist and download
def tile_name(lat, lon):
    return f"n{lat:02d}w{lon:03d}"

def tile_url(lat, lon):
    name = tile_name(lat, lon)
    return f"{S3_BASE}/{name}/USGS_1_{name}.tif"

# Sort tiles for consistent ordering
tile_list = sorted(tiles)

# First pass: check existence and collect valid URLs
print("Checking tile existence...")
valid_tiles = []
for i, (lat, lon) in enumerate(tile_list):
    url = tile_url(lat, lon)
    name = tile_name(lat, lon)
    out_file = f"{OUT_DIR}/USGS_1_{name}.tif"
    
    if os.path.exists(out_file) and os.path.getsize(out_file) > 1000000:
        valid_tiles.append((lat, lon, url, out_file))
        if i % 20 == 0: print(f"  Already downloaded: {name}")
        continue
    
    # Quick HEAD check
    result = subprocess.run(
        ['curl', '-s', '-I', '--max-time', '5', url],
        capture_output=True, text=True
    )
    if '200' in result.stdout.split('\n')[0] if result.stdout else '':
        valid_tiles.append((lat, lon, url, out_file))
    elif i % 30 == 0:
        print(f"  Not found: {name}")

print(f"Valid tiles to download: {len(valid_tiles)}")

# Download in batches of 8 parallel
batch_size = 8
downloaded = 0
skipped = 0
failed = []

for i in range(0, len(valid_tiles), batch_size):
    batch = valid_tiles[i:i+batch_size]
    procs = []
    for lat, lon, url, out_file in batch:
        if os.path.exists(out_file) and os.path.getsize(out_file) > 1000000:
            skipped += 1
            continue
        p = subprocess.Popen(
            ['curl', '-s', '-L', '-o', out_file, '--max-time', '60', url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        procs.append((p, lat, lon, out_file))
    
    for p, lat, lon, out_file in procs:
        ret = p.wait()
        name = tile_name(lat, lon)
        if ret == 0 and os.path.exists(out_file) and os.path.getsize(out_file) > 1000000:
            sz = os.path.getsize(out_file) / 1024 / 1024
            downloaded += 1
            print(f"  [{downloaded}/{len(valid_tiles)}] {name}: {sz:.0f} MB")
        else:
            failed.append(name)
            print(f"  FAILED: {name}")

print(f"\n=== Download complete ===")
print(f"Downloaded: {downloaded}")
print(f"Skipped (already exist): {skipped}")
print(f"Failed: {len(failed)} {failed[:10] if failed else ''}")

total_files = len([f for f in os.listdir(OUT_DIR) if f.endswith('.tif')])
total_size = sum(os.path.getsize(f"{OUT_DIR}/{f}") for f in os.listdir(OUT_DIR) if f.endswith('.tif'))
print(f"Total DEM files: {total_files} ({total_size/1024/1024/1024:.2f} GB)")
print(f"DEM directory: {OUT_DIR}")
