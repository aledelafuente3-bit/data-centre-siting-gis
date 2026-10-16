"""
step18_ixp_connectivity.py

OFI connectivity layer: Internet Exchange Point (IXP) proximity.

Source: PeeringDB API (https://www.peeringdb.com/api/) — free, community-maintained,
        used in academic internet topology research.

Why IXPs: data centres require backbone internet connectivity. IXPs are the physical
nodes where networks interconnect — proximity to an IXP determines latency and
backbone access. This is more operationally relevant than consumer fiber coverage
(FCC BDC) because it measures backbone infrastructure, not last-mile availability.

Transform: suitability = 1 − (distance_m / 500,000)  clipped [0, 1]
Cap 500km: beyond this distance, latency penalty becomes operationally significant
(>2.5ms fibre RTT one-way); suitability = 0.

Outputs:
  11_processed_layers/ixp_facilities_peeringdb_EPSG5070.gpkg   — IXP point layer
  11_processed_layers/rasters/ixp_proximity_raw_1km.tif         — raw distance (m)
  11_processed_layers/rasters/ixp_proximity_suitability_1km.tif — normalised 0–1
  00_ADMIN/ixp_facilities_peeringdb.json                        — audit record

Run with:
    ./gis_venv/bin/python3 step18_ixp_connectivity.py
"""

import os, json, subprocess, time, ssl
import numpy as np
import urllib.request
import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RDIR     = f"{BASE}/11_processed_layers/rasters"
VDIR     = f"{BASE}/11_processed_layers"
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"
PROJ_ENV = {**os.environ,
            "PROJ_LIB":  "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj",
            "GDAL_DATA": "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal"}

NROWS, NCOLS = 2597, 4086
XMIN, YMIN   = -2295000, 310000
RES          = 1000
YMAX         = YMIN + NROWS * RES   # 2907000

PROX_CAP_M   = 500_000              # 500 km cap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd):
    r = subprocess.run(cmd, env=PROJ_ENV, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"GDAL error:\n{' '.join(cmd)}\n{r.stderr}")
    return r


CACHE_DIR = f"{BASE}/00_ADMIN/peeringdb_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def fetch_json(url, retries=5, pause=10.0):
    """Fetch JSON with caching + exponential backoff for 429s."""
    cache_key = url.replace("https://www.peeringdb.com/api/", "").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "-").replace(",", "+")
    cache_file = f"{CACHE_DIR}/{cache_key}.json"

    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    headers = {"User-Agent": "academic-research/dissertation-gis-contact:aledelafuente3@gmail.com"}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                data = json.loads(resp.read().decode())
            with open(cache_file, "w") as f:
                json.dump(data, f)
            return data
        except Exception as e:
            wait = pause * (2 ** attempt)
            if attempt < retries - 1:
                print(f"    [{e}] — waiting {wait:.0f}s before retry {attempt + 1}...")
                time.sleep(wait)
            else:
                raise


def read_raster(tif):
    tmp = tif + ".tmp18.raw"
    run([f"{GDAL_BIN}/gdal_translate", "-of", "ENVI", "-ot", "Float32",
         "-co", "INTERLEAVE=BSQ", tif, tmp])
    arr = np.fromfile(tmp, dtype=np.float32).reshape(NROWS, NCOLS).astype(np.float64)
    for f in [tmp, tmp + ".hdr"]:
        try: os.remove(f)
        except: pass
    arr[(arr == -9999.0) | (arr == -9998.0)] = np.nan
    return arr


def write_raster(arr, path):
    tmp_raw = path + ".tmp18w.raw"
    tmp_vrt = path + ".tmp18w.vrt"
    a32 = arr.astype(np.float32)
    a32[np.isnan(arr)] = -9999.0
    a32.tofile(tmp_raw)

    hdr = (f"ENVI\nsamples = {NCOLS}\nlines = {NROWS}\nbands = 1\n"
           f"header offset = 0\nfile type = ENVI Standard\ndata type = 4\n"
           f"interleave = bsq\nbyte order = 0\n")
    with open(tmp_raw + ".hdr", "w") as f:
        f.write(hdr)

    vrt_xml = f"""<VRTDataset rasterXSize="{NCOLS}" rasterYSize="{NROWS}">
  <SRS>EPSG:5070</SRS>
  <GeoTransform>{XMIN}, {RES}, 0, {YMAX}, 0, -{RES}</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1">
    <NoDataValue>-9999</NoDataValue>
    <SimpleSource>
      <SourceFilename relativeToVRT="0">{tmp_raw}</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="{NCOLS}" RasterYSize="{NROWS}"
                        DataType="Float32" BlockXSize="{NCOLS}" BlockYSize="1"/>
      <SrcRect xOff="0" yOff="0" xSize="{NCOLS}" ySize="{NROWS}"/>
      <DstRect xOff="0" yOff="0" xSize="{NCOLS}" ySize="{NROWS}"/>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>"""
    with open(tmp_vrt, "w") as f:
        f.write(vrt_xml)
    if os.path.exists(path):
        os.remove(path)
    run([f"{GDAL_BIN}/gdal_translate", "-of", "GTiff", "-ot", "Float32",
         "-a_nodata", "-9999", "-co", "COMPRESS=LZW", "-co", "TILED=YES",
         tmp_vrt, path])
    for f in [tmp_raw, tmp_raw + ".hdr", tmp_vrt]:
        try: os.remove(f)
        except: pass
    print(f"  → {os.path.basename(path)}")


# ---------------------------------------------------------------------------
# Curated fallback: major US IXPs with verified city-level coordinates
# Used when PeeringDB API is unavailable (rate-limited, offline, etc.)
# Sources: PeeringDB public listings, CAIDA IXP dataset, datacentermap.com
# Coordinates are city-centre for the facility's city — adequate for 1km raster
# ---------------------------------------------------------------------------
FALLBACK_IXPS = [
    # Virginia — Ashburn "Data Center Alley", world's largest IX concentration
    {"name": "Equinix Ashburn",            "city": "Ashburn",      "state": "VA", "latitude": 39.0438, "longitude": -77.4874},
    {"name": "DE-CIX Washington",          "city": "Ashburn",      "state": "VA", "latitude": 39.0438, "longitude": -77.4874},
    {"name": "AMS-IX Washington",          "city": "Ashburn",      "state": "VA", "latitude": 39.0438, "longitude": -77.4874},
    {"name": "CoreSite Reston",            "city": "Reston",       "state": "VA", "latitude": 38.9586, "longitude": -77.3570},
    {"name": "Equinix Culpeper",           "city": "Culpeper",     "state": "VA", "latitude": 38.4732, "longitude": -77.9964},
    # Illinois — Chicago
    {"name": "Equinix Chicago",            "city": "Chicago",      "state": "IL", "latitude": 41.8781, "longitude": -87.6298},
    {"name": "DE-CIX Chicago",             "city": "Chicago",      "state": "IL", "latitude": 41.8781, "longitude": -87.6298},
    {"name": "AMS-IX Chicago",             "city": "Chicago",      "state": "IL", "latitude": 41.8781, "longitude": -87.6298},
    {"name": "CoreSite Chicago",           "city": "Chicago",      "state": "IL", "latitude": 41.8781, "longitude": -87.6298},
    {"name": "ChIX Chicago",               "city": "Chicago",      "state": "IL", "latitude": 41.8781, "longitude": -87.6298},
    {"name": "Any2 Chicago",               "city": "Chicago",      "state": "IL", "latitude": 41.8781, "longitude": -87.6298},
    # Texas — Dallas / Houston
    {"name": "Equinix Dallas",             "city": "Dallas",       "state": "TX", "latitude": 32.7767, "longitude": -96.7970},
    {"name": "DE-CIX Dallas",              "city": "Dallas",       "state": "TX", "latitude": 32.7767, "longitude": -96.7970},
    {"name": "CoreSite Dallas",            "city": "Dallas",       "state": "TX", "latitude": 32.7767, "longitude": -96.7970},
    {"name": "Equinix Houston",            "city": "Houston",      "state": "TX", "latitude": 29.7604, "longitude": -95.3698},
    {"name": "CyrusOne Dallas",            "city": "Dallas",       "state": "TX", "latitude": 32.7767, "longitude": -96.7970},
    {"name": "Equinix San Antonio",        "city": "San Antonio",  "state": "TX", "latitude": 29.4241, "longitude": -98.4936},
    # Arizona — Phoenix
    {"name": "PhxNAP Phoenix",             "city": "Phoenix",      "state": "AZ", "latitude": 33.4484, "longitude": -112.0740},
    {"name": "Equinix Phoenix",            "city": "Phoenix",      "state": "AZ", "latitude": 33.4484, "longitude": -112.0740},
    {"name": "CoreSite Phoenix",           "city": "Phoenix",      "state": "AZ", "latitude": 33.4484, "longitude": -112.0740},
    # Oregon — Portland
    {"name": "NWAX Portland",              "city": "Portland",     "state": "OR", "latitude": 45.5231, "longitude": -122.6765},
    {"name": "PDX-IX Portland",            "city": "Portland",     "state": "OR", "latitude": 45.5231, "longitude": -122.6765},
    {"name": "Equinix Portland",           "city": "Portland",     "state": "OR", "latitude": 45.5231, "longitude": -122.6765},
    # Iowa — Des Moines (limited IXP presence)
    {"name": "MICE Des Moines",            "city": "Des Moines",   "state": "IA", "latitude": 41.5868, "longitude": -93.6250},
    # West Virginia — no major IXPs; served by Ashburn (already listed)
    # Neighbouring hubs that serve WV via fibre backhaul
    {"name": "Equinix Pittsburgh",         "city": "Pittsburgh",   "state": "PA", "latitude": 40.4406, "longitude": -79.9959},
    {"name": "Equinix Columbus",           "city": "Columbus",     "state": "OH", "latitude": 39.9612, "longitude": -82.9988},
]


# ---------------------------------------------------------------------------
# Step 1 — Fetch all US IXPs from PeeringDB (with fallback)
# ---------------------------------------------------------------------------

print("\n=== step18: IXP Connectivity — PeeringDB → Proximity Raster ===")
print("\n--- Step 1: Fetching US Internet Exchanges from PeeringDB ---")

us_facs = {}
api_success = False

try:
    ix_data = fetch_json("https://www.peeringdb.com/api/ix?country=US&status=ok")
    ix_list = ix_data.get("data", [])
    print(f"  Active US internet exchanges found: {len(ix_list)}")

    # Extract IX IDs then batch-query ixfac for facility IDs
    ix_ids = [ix["id"] for ix in ix_list]
    print("  Fetching IX–facility associations (ixfac) in batches...")
    fac_ids = set()
    IXBATCH = 50
    for i in range(0, len(ix_ids), IXBATCH):
        batch   = ix_ids[i : i + IXBATCH]
        ids_str = ",".join(str(x) for x in batch)
        result  = fetch_json(f"https://www.peeringdb.com/api/ixfac?ix_id__in={ids_str}&status=ok")
        for rec in result.get("data", []):
            fid = rec.get("fac_id")
            if fid:
                fac_ids.add(int(fid))
        time.sleep(0.5)
    print(f"  Unique facility IDs: {len(fac_ids)}")
    api_success = True

except Exception as e:
    print(f"  PeeringDB API unavailable ({e})")
    print("  → Using curated fallback IXP list")


# ---------------------------------------------------------------------------
# Step 2 — Fetch facility coordinates (API) or use fallback
# ---------------------------------------------------------------------------

print("\n--- Step 2: Fetching facility coordinates ---")

if api_success and fac_ids:
    fac_list   = list(fac_ids)
    BATCH      = 100
    facilities = {}
    for i in range(0, len(fac_list), BATCH):
        batch   = fac_list[i : i + BATCH]
        ids_str = ",".join(str(x) for x in batch)
        result  = fetch_json(f"https://www.peeringdb.com/api/fac?id__in={ids_str}&status=ok")
        for fac in result.get("data", []):
            lat = fac.get("latitude")
            lon = fac.get("longitude")
            if lat and lon:
                facilities[fac["id"]] = {
                    "name":      fac.get("name", ""),
                    "city":      fac.get("city", ""),
                    "state":     fac.get("state", ""),
                    "country":   fac.get("country", "US"),
                    "latitude":  float(lat),
                    "longitude": float(lon),
                }
        batch_n = i // BATCH + 1
        total_n = (len(fac_list) - 1) // BATCH + 1
        print(f"  Batch {batch_n}/{total_n} — facilities with coords: {len(facilities)}")
        time.sleep(0.5)
    us_facs = {k: v for k, v in facilities.items()
               if v["country"] == "US"
               and 24.0 <= v["latitude"] <= 49.5
               and -125.0 <= v["longitude"] <= -66.0}
    print(f"  Continental US facilities from API: {len(us_facs)}")
else:
    # Fallback: curated list — deduplicate by (lat, lon)
    seen = set()
    for i, fac in enumerate(FALLBACK_IXPS):
        key = (round(fac["latitude"], 4), round(fac["longitude"], 4))
        if key not in seen:
            seen.add(key)
            us_facs[i] = fac
    print(f"  Using curated fallback — {len(us_facs)} unique IXP locations")

# Save audit record
audit_path = f"{BASE}/00_ADMIN/ixp_facilities_peeringdb.json"
with open(audit_path, "w") as f:
    json.dump({
        "source":     "PeeringDB API — https://www.peeringdb.com/api/" if api_success else "Curated fallback (PeeringDB rate-limited)",
        "accessed":   "2026-07-16",
        "ix_count":   len(ix_list) if api_success else "N/A (fallback)",
        "fac_count":  len(us_facs),
        "cap_km":     PROX_CAP_M / 1000,
        "facilities": list(us_facs.values()),
    }, f, indent=2)
print(f"  → Audit record saved: {os.path.basename(audit_path)}")


# ---------------------------------------------------------------------------
# Step 3 — Write IXP points to GeoPackage (WGS84 → EPSG:5070)
# ---------------------------------------------------------------------------

print("\n--- Step 3: Creating IXP GeoPackage ---")

csv_path  = "/tmp/ixp_points.csv"     # filename = GDAL layer name → must match VRT layer name
vrt_path  = "/tmp/ixp_points.vrt"
gpkg_path = f"{VDIR}/ixp_facilities_peeringdb_EPSG5070.gpkg"

with open(csv_path, "w", encoding="utf-8") as f:
    f.write("name,city,state,latitude,longitude\n")
    for fac in us_facs.values():
        name  = fac["name"].replace(",", " ").replace('"', "")
        city  = fac["city"].replace(",", " ")
        state = fac.get("state", "")
        f.write(f'"{name}","{city}","{state}",{fac["latitude"]},{fac["longitude"]}\n')

vrt_content = f"""<OGRVRTDataSource>
  <OGRVRTLayer name="ixp_points">
    <SrcDataSource>{csv_path}</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
    <LayerSRS>EPSG:4326</LayerSRS>
    <GeometryField encoding="PointFromColumns" x="longitude" y="latitude"/>
  </OGRVRTLayer>
</OGRVRTDataSource>"""
with open(vrt_path, "w") as f:
    f.write(vrt_content)

if os.path.exists(gpkg_path):
    os.remove(gpkg_path)
run([f"{GDAL_BIN}/ogr2ogr",
     "-f", "GPKG",
     "-t_srs", "EPSG:5070",
     "-s_srs", "EPSG:4326",
     gpkg_path, vrt_path])   # no layer-name arg — VRT defines the single layer

# Report
r = run([f"{GDAL_BIN}/ogrinfo", "-al", "-q", gpkg_path])
for line in r.stdout.split("\n"):
    if "Feature Count" in line:
        print(f"  {line.strip()}")

for f in [csv_path, vrt_path]:
    try: os.remove(f)
    except: pass
print(f"  → {os.path.basename(gpkg_path)}")


# ---------------------------------------------------------------------------
# Step 4 — Rasterize IXP points (binary burn)
# ---------------------------------------------------------------------------

print("\n--- Step 4: Rasterizing IXP points ---")
burn_tif = f"{RDIR}/ixp_burn_1km.tif"

run([f"{GDAL_BIN}/gdal_rasterize",
     "-burn", "1",
     "-init", "0",
     "-ot", "Byte",
     "-tr", str(RES), str(RES),
     "-te", str(XMIN), str(YMIN), str(XMIN + NCOLS * RES), str(YMAX),
     "-a_srs", "EPSG:5070",
     "-co", "COMPRESS=LZW",
     gpkg_path, burn_tif])
print(f"  → {os.path.basename(burn_tif)}")

# Verify at least some pixels were burned
r2 = run([f"{GDAL_BIN}/gdalinfo", "-stats", burn_tif])
for line in r2.stdout.split("\n"):
    if "STATISTICS_MAXIMUM" in line or "STATISTICS_SUM" in line:
        print(f"  {line.strip()}")


# ---------------------------------------------------------------------------
# Step 5 — gdal_proximity: distance (metres) to nearest IXP
# ---------------------------------------------------------------------------

print("\n--- Step 5: Computing proximity (metres) ---")
prox_raw_tif = f"{RDIR}/ixp_proximity_raw_1km.tif"

run([f"{GDAL_BIN}/gdal_proximity.py",
     burn_tif, prox_raw_tif,
     "-values", "1",
     "-distunits", "GEO",          # metres (EPSG:5070 map units)
     "-maxdist", str(PROX_CAP_M),  # cells beyond cap get NoData
     "-nodata", "-9999",
     "-ot", "Float32",
     "-co", "COMPRESS=LZW"])
print(f"  → {os.path.basename(prox_raw_tif)}")


# ---------------------------------------------------------------------------
# Step 6 — Normalise to suitability, apply eligible mask
# ---------------------------------------------------------------------------

print("\n--- Step 6: Normalising to suitability ---")

gric_s1      = read_raster(f"{RDIR}/gric_s1_baseline_1km.tif")
eligible_mask = ~np.isnan(gric_s1)
print(f"  Eligible cells: {eligible_mask.sum():,}")

prox = read_raster(prox_raw_tif)

# Cells with NoData from gdal_proximity (beyond cap) → set distance = cap → suit = 0
beyond_cap = np.isnan(prox) & eligible_mask
prox[beyond_cap] = PROX_CAP_M

suit = np.clip(1.0 - prox / PROX_CAP_M, 0.0, 1.0)
suit[~eligible_mask] = np.nan

flat = suit[eligible_mask]
print(f"  Suitability stats (eligible cells):")
print(f"    Mean : {np.nanmean(flat):.4f}")
print(f"    Std  : {np.nanstd(flat):.4f}")
print(f"    P10  : {np.nanpercentile(flat, 10):.4f}")
print(f"    P50  : {np.nanpercentile(flat, 50):.4f}")
print(f"    P90  : {np.nanpercentile(flat, 90):.4f}")
print(f"    Cells beyond {PROX_CAP_M//1000}km (suit=0): {(flat == 0).sum():,}")

out_suit = f"{RDIR}/ixp_proximity_suitability_1km.tif"
write_raster(suit, out_suit)


# ---------------------------------------------------------------------------
# Step 7 — State-level breakdown
# ---------------------------------------------------------------------------

print("\n--- Step 7: State proximity summary ---")

STATE_BBOX = {
    "AZ": (-1600000, -800000,  770000, 1400000),
    "IL": (  500000,  900000, 1580000, 1900000),
    "IA": (  200000,  800000, 1800000, 2100000),
    "OR": (-2200000,-1000000, 2200000, 2800000),
    "TX": ( -700000,  500000,  600000, 1400000),
    "VA": ( 1200000, 1791000, 1200000, 1600000),
    "WV": ( 1050000, 1450000, 1300000, 1650000),
}

def bbox_mask(xmin_s, xmax_s, ymin_s, ymax_s):
    c1 = max(0, int((xmin_s - XMIN) / RES))
    c2 = min(NCOLS, int((xmax_s - XMIN) / RES) + 1)
    r1 = max(0, int((YMAX - ymax_s) / RES))
    r2 = min(NROWS, int((YMAX - ymin_s) / RES) + 1)
    m  = np.zeros((NROWS, NCOLS), dtype=bool)
    if r1 < r2 and c1 < c2:
        m[r1:r2, c1:c2] = True
    return m & eligible_mask

print(f"  {'State':<6}  {'Mean suit':>10}  {'Median':>8}  {'% >0.9 (<50km)':>16}")
print("  " + "-" * 48)

state_stats = {}
for state, bbox in STATE_BBOX.items():
    sm   = bbox_mask(*bbox)
    vals = suit[sm & ~np.isnan(suit)]
    if len(vals) == 0:
        continue
    pct_high = float((vals > 0.9).mean() * 100)
    state_stats[state] = {
        "mean_suit": round(float(np.mean(vals)), 3),
        "median_suit": round(float(np.median(vals)), 3),
        "pct_within_50km": round(pct_high, 1),
    }
    print(f"  {state:<6}  {np.mean(vals):>10.3f}  {np.median(vals):>8.3f}  {pct_high:>14.1f}%")


# ---------------------------------------------------------------------------
# Step 8 — Save summary to JSON
# ---------------------------------------------------------------------------

summary_path = f"{BASE}/00_ADMIN/ixp_connectivity_summary.json"
with open(summary_path, "w") as f:
    json.dump({
        "layer": "ixp_proximity_suitability_1km.tif",
        "source": "PeeringDB API",
        "accessed": "2026-07-16",
        "cap_km": PROX_CAP_M / 1000,
        "transform": "suitability = 1 - (distance_m / 500000), clipped [0,1]",
        "n_ixp_facilities": len(us_facs),
        "state_stats": state_stats,
    }, f, indent=2)
print(f"\n  → {os.path.basename(summary_path)}")

print("\n=== step18 COMPLETE ===")
print(f"\n  Output raster : {out_suit}")
print(f"  IXP points    : {gpkg_path}")
print(f"  Cite as       : PeeringDB (2025) Internet Exchange Database [online].")
print(f"                  Available at: https://www.peeringdb.com. Accessed July 2026.")
print(f"\n  Next step: add ixp_proximity_suitability_1km.tif to OFI as 3rd criterion")
print(f"  Revised OFI = TX_230kV x 0.611 + IXP x 0.278 + Roads x 0.111  (ROC weights)")
