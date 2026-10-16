#!/usr/bin/env python3
"""Step 3: EJI download — fixed pagination (use count-based loop, not exceededTransferLimit)."""
import subprocess, json, os, time, math

OUT_DIR = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/01_RAW_DATA/social_equity/eji_2024"
os.makedirs(OUT_DIR, exist_ok=True)

BASE_URL = "https://onemap.cdc.gov/onemapservices/rest/services/Hosted/Environmental_Justice_Index_2022_Hosted/FeatureServer/0"
QUERY_URL = f"{BASE_URL}/query"
STATE_FIPS = ['04','17','19','41','48','51','54']
PAGE_SIZE = 2000

def query_page(params, timeout=90):
    import urllib.parse
    data = urllib.parse.urlencode(params).encode()
    result = subprocess.run(
        ['curl', '-sk', '--max-time', str(timeout), '-X', 'POST', '--data', data.decode(), QUERY_URL],
        capture_output=True, text=True
    )
    if not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

fips_list = "','".join(STATE_FIPS)
WHERE = f"statefp IN ('{fips_list}')"

# Get total count
count_resp = query_page({'where': WHERE, 'returnCountOnly': 'true', 'f': 'json'})
total = count_resp.get('count', 0) if count_resp else 0
n_pages = math.ceil(total / PAGE_SIZE)
print(f"Total tracts in 7 states: {total} ({n_pages} pages)")

all_features = []
for page_idx in range(n_pages):
    offset = page_idx * PAGE_SIZE
    resp = query_page({
        'where': WHERE,
        'outFields': '*',
        'resultRecordCount': PAGE_SIZE,
        'resultOffset': offset,
        'outSR': '4326',
        'returnGeometry': 'true',
        'f': 'geojson'
    }, timeout=120)
    
    if resp is None:
        print(f"  ERROR page {page_idx+1}/{n_pages}, retrying...")
        time.sleep(5)
        resp = query_page({
            'where': WHERE, 'outFields': '*',
            'resultRecordCount': PAGE_SIZE, 'resultOffset': offset,
            'outSR': '4326', 'returnGeometry': 'true', 'f': 'geojson'
        }, timeout=120)
        if resp is None:
            print(f"  FAILED page {page_idx+1}, skipping")
            continue
    
    feats = resp.get('features', [])
    all_features.extend(feats)
    print(f"  Page {page_idx+1}/{n_pages}: {len(feats)} tracts | Total: {len(all_features)}")
    time.sleep(0.2)

# Save GeoJSON
out_geojson = f"{OUT_DIR}/eji_2022_7states.geojson"
with open(out_geojson, 'w') as f:
    json.dump({'type': 'FeatureCollection', 'features': all_features}, f)
sz = os.path.getsize(out_geojson) / 1024 / 1024
print(f"\nSaved: {out_geojson} ({len(all_features)} tracts, {sz:.1f} MB)")

# Print key field names
if all_features:
    props = all_features[0].get('properties', {})
    eji_fields = sorted([k for k in props if any(x in k.lower() for x in ['eji','ebm','svm','hvm','rpl','spl'])])
    print(f"Key EJI fields: {eji_fields}")
