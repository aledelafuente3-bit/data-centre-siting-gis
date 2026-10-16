#!/usr/bin/env python3
"""
Step 6: Data-centre validation pipeline
- Reads geocoded.csv (commercial DC directory, NOT OSM)
- Converts to EPSG:5070 GeoPackage, clips to 7-state mask
- Extracts raster scores at validation points
- Generates 5,000 constrained random eligible points
- Extracts scores at random points
- Computes capture rates
"""
import os, sys, csv, random, math

os.environ['PROJ_LIB']  = '/Applications/QGIS-LTR.app/Contents/Resources/proj'
os.environ['PROJ_DATA'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj'

from osgeo import ogr, osr, gdal
gdal.UseExceptions()

BASE     = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RAW_CSV  = f"{BASE}/10_data_centers_validation/raw/geocoded.csv"
MASK     = f"{BASE}/11_processed_layers/rasters/mask_7states_1km_EPSG5070.tif"
VAL_GPKG = f"{BASE}/06_VALIDATION/observed_data_center_points/data_centers_7state_EPSG5070.gpkg"
RAND_GPKG= f"{BASE}/06_VALIDATION/constrained_random_points/random_eligible_5000_EPSG5070.gpkg"
DC_CSV   = f"{BASE}/06_VALIDATION/extracted_scores/data_center_scores.csv"
RAND_CSV = f"{BASE}/06_VALIDATION/extracted_scores/random_scores.csv"

RASTER_LAYERS = {
    'tx_230kV_prox_m':    f"{BASE}/11_processed_layers/rasters/hifld_tx_230kV_proximity_1km.tif",
    'tx_345kV_prox_m':    f"{BASE}/11_processed_layers/rasters/hifld_tx_345kV_proximity_1km.tif",
    'substation_prox_m':  f"{BASE}/11_processed_layers/rasters/hifld_substations_IN_SERVICE_proximity_1km.tif",
    'carbon_suit':        f"{BASE}/11_processed_layers/rasters/carbon_current_co2e_suitability.tif",
    'water_suit':         f"{BASE}/11_processed_layers/rasters/water_stress_baseline_bws_suitability.tif",
    'wildfire_score':     f"{BASE}/11_processed_layers/rasters/nri_wildfire_score_1km.tif",
    'flood_score':        f"{BASE}/11_processed_layers/rasters/nri_inland_flood_score_1km.tif",
    'heat_days_2041_60':  f"{BASE}/11_processed_layers/rasters/nexgddp_mean_days_gt35_2041_2060.tif",
    'pct_eligible':       f"{BASE}/11_processed_layers/rasters/pct_eligible_1km_EPSG5070.tif",
    'pct_waterwetland':   f"{BASE}/11_processed_layers/rasters/pct_waterwetland_1km_EPSG5070.tif",
}

# ─── CRS setup ────────────────────────────────────────────────────────────────
wgs84 = osr.SpatialReference(); wgs84.ImportFromEPSG(4326)
wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
albers = osr.SpatialReference(); albers.ImportFromEPSG(5070)
albers.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
t_fwd = osr.CoordinateTransformation(wgs84, albers)

# ─── Load mask raster ─────────────────────────────────────────────────────────
print("Loading mask raster...")
mask_ds = gdal.Open(MASK)
mask_gt = mask_ds.GetGeoTransform()  # xmin, xres, 0, ymax, 0, -yres
mask_band = mask_ds.GetRasterBand(1)
mask_arr = mask_band.ReadAsArray()
nrows, ncols = mask_arr.shape
xmin = mask_gt[0]; xres = mask_gt[1]; ymax = mask_gt[3]; yres = abs(mask_gt[5])
print(f"  Mask: {ncols}×{nrows}, xmin={xmin:.0f}, ymax={ymax:.0f}, cell={xres:.0f}m")
print(f"  Valid cells (mask=1): {(mask_arr == 1).sum()}")

def xy_to_rowcol(x, y):
    col = int((x - xmin) / xres)
    row = int((ymax - y) / yres)
    return row, col

def sample_raster(ds, x5070, y5070):
    """Sample raster value at EPSG:5070 coordinate."""
    gt = ds.GetGeoTransform()
    col = int((x5070 - gt[0]) / gt[1])
    row = int((y5070 - gt[3]) / gt[5])
    if col < 0 or row < 0 or col >= ds.RasterXSize or row >= ds.RasterYSize:
        return None
    band = ds.GetRasterBand(1)
    val = band.ReadAsArray(col, row, 1, 1)
    if val is None:
        return None
    v = float(val[0][0])
    nd = band.GetNoDataValue()
    if nd is not None and abs(v - nd) < 0.001:
        return None
    return v

# ─── Open all score rasters ───────────────────────────────────────────────────
print("Opening score rasters...")
raster_ds = {}
for key, path in RASTER_LAYERS.items():
    if os.path.exists(path):
        raster_ds[key] = gdal.Open(path)
        print(f"  OK: {key}")
    else:
        print(f"  MISSING: {key} ({path})")

# ─── Task B: Convert geocoded.csv → GPKG, clip to mask ───────────────────────
print("\n=== Task B: Converting geocoded.csv to GPKG ===")
rows_in = []
with open(RAW_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows_in.append(r)
print(f"  Input rows: {len(rows_in)}")

driver = ogr.GetDriverByName('GPKG')
if os.path.exists(VAL_GPKG): driver.DeleteDataSource(VAL_GPKG)
ds_out = driver.CreateDataSource(VAL_GPKG)
lyr = ds_out.CreateLayer('data_centers', srs=albers, geom_type=ogr.wkbPoint)
for fn in ['name','address','city','state','zip','source_note','latitude','longitude','x_5070','y_5070']:
    fd = ogr.FieldDefn(fn, ogr.OFTString if fn not in ('latitude','longitude','x_5070','y_5070') else ogr.OFTReal)
    fd.SetWidth(255)
    lyr.CreateField(fd)
defn = lyr.GetLayerDefn()

valid_points = []
skipped = 0
for r in rows_in:
    try:
        lat = float(r.get('latitude',''))
        lon = float(r.get('longitude',''))
    except (ValueError, TypeError):
        skipped += 1; continue
    if abs(lat) < 1 or abs(lon) > 180:
        skipped += 1; continue
    
    # Transform to EPSG:5070
    pt_geom = ogr.Geometry(ogr.wkbPoint)
    pt_geom.AddPoint(lon, lat)
    pt_geom.Transform(t_fwd)
    x5070, y5070 = pt_geom.GetX(), pt_geom.GetY()
    
    # Check mask
    row_idx, col_idx = xy_to_rowcol(x5070, y5070)
    if row_idx < 0 or col_idx < 0 or row_idx >= nrows or col_idx >= ncols:
        skipped += 1; continue
    if mask_arr[row_idx, col_idx] != 1:
        skipped += 1; continue
    
    feat = ogr.Feature(defn)
    feat.SetGeometry(pt_geom)
    feat.SetField('name',        r.get('name',''))
    feat.SetField('address',     r.get('address',''))
    feat.SetField('city',        r.get('city',''))
    feat.SetField('state',       r.get('state',''))
    feat.SetField('zip',         r.get('zip',''))
    feat.SetField('source_note', 'Commercial data centre directory (Datacenter Hawk/CBRE format - unconfirmed); geocoded from address; NOT OSM')
    feat.SetField('latitude',    lat)
    feat.SetField('longitude',   lon)
    feat.SetField('x_5070',      x5070)
    feat.SetField('y_5070',      y5070)
    lyr.CreateFeature(feat)
    valid_points.append({'name':r.get('name',''),'state':r.get('state',''),'city':r.get('city',''),
                         'x_5070':x5070,'y_5070':y5070,'lat':lat,'lon':lon})

ds_out.FlushCache(); ds_out = None
print(f"  Valid points in mask: {len(valid_points)}")
print(f"  Skipped:              {skipped}")

# ─── Task C: Extract scores at validation points ───────────────────────────────
print("\n=== Task C: Extracting scores at validation points ===")
score_cols = list(RASTER_LAYERS.keys())
dc_rows = []
for pt in valid_points:
    row_out = {
        'name': pt['name'], 'state': pt['state'], 'city': pt['city'],
        'x_5070': pt['x_5070'], 'y_5070': pt['y_5070'],
        'latitude': pt['lat'], 'longitude': pt['lon'],
    }
    for key in score_cols:
        if key in raster_ds:
            row_out[key] = sample_raster(raster_ds[key], pt['x_5070'], pt['y_5070'])
        else:
            row_out[key] = None
    dc_rows.append(row_out)

with open(DC_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['name','state','city','x_5070','y_5070','latitude','longitude'] + score_cols)
    writer.writeheader()
    writer.writerows(dc_rows)
print(f"  Saved: {DC_CSV} ({len(dc_rows)} rows)")

# Check NoData rate
for key in ['tx_230kV_prox_m', 'carbon_suit', 'water_suit']:
    nd_count = sum(1 for r in dc_rows if r.get(key) is None)
    print(f"  NoData in {key}: {nd_count}/{len(dc_rows)} ({100*nd_count/len(dc_rows):.1f}%)")

# ─── Task D: Generate 5,000 constrained random eligible points ─────────────────
print("\n=== Task D: Generating 5,000 random eligible points ===")
random.seed(42)

# Load pct_eligible and pct_waterwetland for eligibility filter
pct_elig_ds = raster_ds.get('pct_eligible')
pct_wet_ds  = raster_ds.get('pct_waterwetland')

# Build eligible cell list
eligible_cells = []
if pct_elig_ds and pct_wet_ds:
    elig_arr = pct_elig_ds.GetRasterBand(1).ReadAsArray()
    wet_arr  = pct_wet_ds.GetRasterBand(1).ReadAsArray()
    elig_gt  = pct_elig_ds.GetGeoTransform()
    elig_nd  = pct_elig_ds.GetRasterBand(1).GetNoDataValue() or -9999
    wet_nd   = pct_wet_ds.GetRasterBand(1).GetNoDataValue() or -9999
    
    for r in range(nrows):
        for c in range(ncols):
            if mask_arr[r, c] != 1:
                continue
            ev = float(elig_arr[r, c]) if elig_arr is not None else 100
            wv = float(wet_arr[r, c]) if wet_arr is not None else 0
            if ev == elig_nd or wv == wet_nd:
                continue
            if ev >= 10 and wv <= 50:
                cx = xmin + c * xres + xres / 2
                cy = ymax - r * yres - yres / 2
                eligible_cells.append((r, c, cx, cy))
    print(f"  Eligible cells: {len(eligible_cells):,}")
else:
    # Fallback: all mask cells
    for r in range(nrows):
        for c in range(ncols):
            if mask_arr[r, c] == 1:
                cx = xmin + c * xres + xres / 2
                cy = ymax - r * yres - yres / 2
                eligible_cells.append((r, c, cx, cy))
    print(f"  Using all mask cells (rasters unavailable): {len(eligible_cells):,}")

# Sample 5000 random points (simple random — proportional by drawing from pool)
sample_size = min(5000, len(eligible_cells))
sampled = random.sample(eligible_cells, sample_size)
print(f"  Sampled: {len(sampled)} points")

# Save to GPKG
if os.path.exists(RAND_GPKG): driver.DeleteDataSource(RAND_GPKG)
ds_rand = driver.CreateDataSource(RAND_GPKG)
lyr_rand = ds_rand.CreateLayer('random_eligible', srs=albers, geom_type=ogr.wkbPoint)
for fn, ft in [('point_id', ogr.OFTInteger), ('x_5070', ogr.OFTReal), ('y_5070', ogr.OFTReal)]:
    lyr_rand.CreateField(ogr.FieldDefn(fn, ft))
defn_rand = lyr_rand.GetLayerDefn()

rand_points = []
for i, (r, c, cx, cy) in enumerate(sampled):
    # Add small jitter ±400m
    jx = random.uniform(-400, 400)
    jy = random.uniform(-400, 400)
    px, py = cx + jx, cy + jy
    
    pt_g = ogr.Geometry(ogr.wkbPoint)
    pt_g.AddPoint(px, py)
    feat = ogr.Feature(defn_rand)
    feat.SetGeometry(pt_g)
    feat.SetField('point_id', i + 1)
    feat.SetField('x_5070', px)
    feat.SetField('y_5070', py)
    lyr_rand.CreateFeature(feat)
    rand_points.append({'point_id': i+1, 'x_5070': px, 'y_5070': py})

ds_rand.FlushCache(); ds_rand = None
print(f"  Saved: {RAND_GPKG}")

# ─── Task E: Extract scores at random points ───────────────────────────────────
print("\n=== Task E: Extracting scores at random points ===")
rand_rows = []
for pt in rand_points:
    row_out = {'point_id': pt['point_id'], 'x_5070': pt['x_5070'], 'y_5070': pt['y_5070']}
    for key in score_cols:
        if key in raster_ds:
            row_out[key] = sample_raster(raster_ds[key], pt['x_5070'], pt['y_5070'])
        else:
            row_out[key] = None
    rand_rows.append(row_out)

with open(RAND_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['point_id','x_5070','y_5070'] + score_cols)
    writer.writeheader()
    writer.writerows(rand_rows)
print(f"  Saved: {RAND_CSV} ({len(rand_rows)} rows)")

# ─── Task F: Capture rates and summary stats ───────────────────────────────────
print("\n=== Task F: Computing capture rates ===")

# Gather values where not None
def vals(rows, key):
    return [r[key] for r in rows if r.get(key) is not None]

# 230kV proximity — lower = better; compute thresholds from ALL eligible cells
prox_dc   = sorted(v for v in vals(dc_rows,   'tx_230kV_prox_m') if v is not None)
prox_rand = sorted(v for v in vals(rand_rows, 'tx_230kV_prox_m') if v is not None)

all_prox = prox_rand  # use random as proxy for study-area distribution
if all_prox:
    n_all = len(all_prox)
    p10_thresh = all_prox[int(0.10 * n_all)]
    p20_thresh = all_prox[int(0.20 * n_all)]
    p30_thresh = all_prox[int(0.30 * n_all)]
    
    print(f"\n  230kV proximity thresholds (top = lowest):")
    print(f"    Top 10%: ≤ {p10_thresh:.0f} m")
    print(f"    Top 20%: ≤ {p20_thresh:.0f} m")
    print(f"    Top 30%: ≤ {p30_thresh:.0f} m")
    
    dc_p10 = sum(1 for v in prox_dc if v <= p10_thresh) / len(prox_dc) * 100 if prox_dc else 0
    dc_p20 = sum(1 for v in prox_dc if v <= p20_thresh) / len(prox_dc) * 100 if prox_dc else 0
    dc_p30 = sum(1 for v in prox_dc if v <= p30_thresh) / len(prox_dc) * 100 if prox_dc else 0
    
    print(f"\n  Capture rates (validation DCs in top X% of 230kV proximity):")
    print(f"    Top 10%: {dc_p10:.1f}%  (expected baseline ~10%)")
    print(f"    Top 20%: {dc_p20:.1f}%  (expected baseline ~20%)")
    print(f"    Top 30%: {dc_p30:.1f}%  (expected baseline ~30%)")

# Mean comparisons
for key in ['tx_230kV_prox_m','carbon_suit','water_suit','wildfire_score','flood_score']:
    dc_v  = vals(dc_rows,   key)
    rnd_v = vals(rand_rows, key)
    if dc_v and rnd_v:
        dc_mean  = sum(dc_v)  / len(dc_v)
        rnd_mean = sum(rnd_v) / len(rnd_v)
        print(f"\n  {key}:")
        print(f"    DC mean:     {dc_mean:.4f}  (n={len(dc_v)})")
        print(f"    Random mean: {rnd_mean:.4f}  (n={len(rnd_v)})")
        print(f"    Ratio DC/Random: {dc_mean/rnd_mean:.3f}")

# Per-state 230kV proximity at DC points
print(f"\n  Mean 230kV proximity by state (at DC validation points):")
state_prox = {}
for r in dc_rows:
    s = r.get('state','')
    v = r.get('tx_230kV_prox_m')
    if s and v is not None:
        state_prox.setdefault(s, []).append(v)
for s in sorted(state_prox):
    vv = state_prox[s]
    print(f"    {s}: mean={sum(vv)/len(vv):.0f}m  n={len(vv)}")

print("\n=== Step 6 complete ===")
print(f"  Output files:")
print(f"    {VAL_GPKG}")
print(f"    {RAND_GPKG}")
print(f"    {DC_CSV}")
print(f"    {RAND_CSV}")

# Store capture rates for summary doc
CAPTURE = {
    'n_dc': len(valid_points),
    'n_rand': len(rand_points),
    'p10_thresh': p10_thresh if all_prox else 0,
    'p20_thresh': p20_thresh if all_prox else 0,
    'p30_thresh': p30_thresh if all_prox else 0,
    'dc_p10': dc_p10 if all_prox else 0,
    'dc_p20': dc_p20 if all_prox else 0,
    'dc_p30': dc_p30 if all_prox else 0,
}
print(f"\nCAPTURE_STATS={CAPTURE}")
