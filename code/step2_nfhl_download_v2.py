#!/usr/bin/env python3
"""
Step 2 v2: NFHL download — download remaining states (skip AZ, already done).
Downloads SFHA zones only, geometry + minimal fields.
Skips states already downloaded.
"""
import os, subprocess, json, time, urllib.parse

BASE    = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
OUT_DIR = f"{BASE}/07_hazards/raw/flood/nfhl"
QUERY   = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
AVAIL_Q = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/0/query"

STATES = {
    'AZ': '-115.2,30.8,-108.8,37.7',
    'IL': '-91.7,36.7,-86.8,42.7',
    'IA': '-97.0,40.1,-90.0,43.8',
    'OR': '-125.0,41.7,-116.2,46.5',
    'TX': '-107.0,25.6,-93.3,36.7',
    'VA': '-84.0,36.3,-75.0,39.7',
    'WV': '-83.0,37.0,-77.5,40.8',
}

SFHA_WHERE = "FLD_ZONE IN ('A','AE','AO','AH','AR','A99','VE','V')"
PAGE_SIZE = 2000

def post_query(url, params, timeout=90):
    data = urllib.parse.urlencode(params).encode()
    r = subprocess.run(['curl', '-sk', '--max-time', str(timeout),
                        '-X', 'POST', '--data', data.decode(), url],
                       capture_output=True, text=True)
    if not r.stdout.strip(): return None
    try: return json.loads(r.stdout)
    except: return None

def download_state(state, bbox, url, where, outfile, fields='FLD_ZONE,ZONE_SUBTY'):
    """Download all pages for one state to GeoJSON."""
    if os.path.exists(outfile) and os.path.getsize(outfile) > 10000:
        sz = os.path.getsize(outfile)/1024/1024
        print(f"  {state}: Already downloaded ({sz:.0f} MB) — skipping")
        return True
    
    # Get count
    count_resp = post_query(url, {
        'where': where, 'geometry': bbox, 'geometryType': 'esriGeometryEnvelope',
        'spatialRel': 'esriSpatialRelIntersects', 'returnCountOnly': 'true', 'f': 'json'
    })
    total = count_resp.get('count', 0) if count_resp else 0
    import math
    n_pages = math.ceil(total / PAGE_SIZE)
    print(f"  {state}: {total} records ({n_pages} pages)")
    
    all_feats = []
    for page in range(n_pages):
        offset = page * PAGE_SIZE
        resp = post_query(url, {
            'where': where, 'geometry': bbox, 'geometryType': 'esriGeometryEnvelope',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': fields,
            'resultRecordCount': PAGE_SIZE, 'resultOffset': offset,
            'outSR': '4326', 'returnGeometry': 'true', 'f': 'geojson'
        }, timeout=120)
        
        if resp is None:
            print(f"    Page {page+1}/{n_pages}: TIMEOUT, retrying...")
            time.sleep(5)
            resp = post_query(url, {
                'where': where, 'geometry': bbox, 'geometryType': 'esriGeometryEnvelope',
                'spatialRel': 'esriSpatialRelIntersects',
                'outFields': fields,
                'resultRecordCount': PAGE_SIZE, 'resultOffset': offset,
                'outSR': '4326', 'returnGeometry': 'true', 'f': 'geojson'
            }, timeout=120)
            if resp is None:
                print(f"    Page {page+1}/{n_pages}: FAILED — skipping")
                continue
        
        feats = resp.get('features', [])
        all_feats.extend(feats)
        if page % 10 == 0 or page == n_pages - 1:
            print(f"    Page {page+1}/{n_pages}: {len(feats)} features | Running: {len(all_feats)}")
        time.sleep(0.2)
    
    with open(outfile, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': all_feats}, f)
    sz = os.path.getsize(outfile)/1024/1024
    print(f"  {state}: DONE — {len(all_feats)} features, {sz:.0f} MB → {outfile}")
    return True

print("=== NFHL Download v2 (resumable) ===")
for state, bbox in STATES.items():
    print(f"\n--- {state} ---")
    sfha_out = f"{OUT_DIR}/nfhl_sfha_{state.lower()}.geojson"
    download_state(state, bbox, QUERY, SFHA_WHERE, sfha_out)

print("\n=== Downloading Availability (Layer 0) ===")
for state, bbox in STATES.items():
    avail_out = f"{OUT_DIR}/nfhl_avail_{state.lower()}.geojson"
    if os.path.exists(avail_out) and os.path.getsize(avail_out) > 1000:
        print(f"  {state} avail: already done")
        continue
    print(f"\n--- {state} availability ---")
    download_state(state, bbox, AVAIL_Q, "1=1", avail_out, fields='SHAPE')

print("\n=== All downloads complete ===")
import os
for f in sorted(os.listdir(OUT_DIR)):
    path = f"{OUT_DIR}/{f}"
    print(f"  {f}: {os.path.getsize(path)/1024/1024:.1f} MB")
