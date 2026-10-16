#!/usr/bin/env python3
"""
Step 2 NFHL retry — re-download states that came back empty (IA, TX, VA).
Uses sub-bounding-box tiling to avoid API timeout on large record counts.
"""
import os, subprocess, json, time, urllib.parse, math

BASE    = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
OUT_DIR = f"{BASE}/07_hazards/raw/flood/nfhl"
QUERY   = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
AVAIL_Q = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/0/query"

SFHA_WHERE = "FLD_ZONE IN ('A','AE','AO','AH','AR','A99','VE','V')"
PAGE_SIZE = 1000  # Smaller page size for better reliability

# States that came back empty — split into sub-tiles
RETRY_STATES = {
    'IA': [  # Iowa: split into 4 east-west tiles
        '-97.0,40.1,-93.5,43.8',
        '-93.5,40.1,-90.0,43.8',
    ],
    'TX': [  # Texas: large state, split into 6 tiles
        '-107.0,25.6,-102.0,30.0',
        '-107.0,30.0,-102.0,36.7',
        '-102.0,25.6,-97.0,30.0',
        '-102.0,30.0,-97.0,36.7',
        '-97.0,25.6,-93.3,30.0',
        '-97.0,30.0,-93.3,36.7',
    ],
    'VA': [  # Virginia: split into 2 tiles
        '-84.0,36.3,-79.5,39.7',
        '-79.5,36.3,-75.0,39.7',
    ],
    'WV': [  # West Virginia: one tile (retry if needed)
        '-83.0,37.0,-77.5,40.8',
    ],
}

def post_query(url, params, timeout=120):
    data = urllib.parse.urlencode(params).encode()
    r = subprocess.run(['curl', '-sk', '--max-time', str(timeout),
                        '-X', 'POST', '--data', data.decode(), url],
                       capture_output=True, text=True)
    if not r.stdout.strip(): return None
    try: return json.loads(r.stdout)
    except: return None

def download_bbox(state, bbox, url, where, fields='FLD_ZONE,ZONE_SUBTY'):
    """Download all pages for one bbox tile. Returns list of features."""
    # Get count
    count_resp = post_query(url, {
        'where': where, 'geometry': bbox, 'geometryType': 'esriGeometryEnvelope',
        'spatialRel': 'esriSpatialRelIntersects', 'returnCountOnly': 'true', 'f': 'json'
    }, timeout=60)

    if not count_resp:
        print(f"    [{bbox}]: COUNT TIMEOUT — will try anyway with pages")
        total = 10000  # assume large; try up to 10 pages
    else:
        total = count_resp.get('count', 0)

    if total == 0:
        print(f"    [{bbox}]: 0 records")
        return []

    n_pages = math.ceil(total / PAGE_SIZE)
    print(f"    [{bbox}]: {total} records → {n_pages} pages")

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
            print(f"      Page {page+1}/{n_pages}: TIMEOUT, retrying...")
            time.sleep(10)
            resp = post_query(url, {
                'where': where, 'geometry': bbox, 'geometryType': 'esriGeometryEnvelope',
                'spatialRel': 'esriSpatialRelIntersects',
                'outFields': fields,
                'resultRecordCount': PAGE_SIZE, 'resultOffset': offset,
                'outSR': '4326', 'returnGeometry': 'true', 'f': 'geojson'
            }, timeout=180)

        if resp is None:
            print(f"      Page {page+1}/{n_pages}: FAILED AGAIN — skipping this page")
            continue

        feats = resp.get('features', [])
        if not feats:
            break  # No more data
        all_feats.extend(feats)
        print(f"      Page {page+1}/{n_pages}: +{len(feats)} | total {len(all_feats)}")
        time.sleep(0.5)

    return all_feats

def download_state(state, bbox_list, url, where, outfile, fields='FLD_ZONE,ZONE_SUBTY'):
    """Download state via multiple bbox tiles if needed."""
    # Check if already downloaded with actual data
    if os.path.exists(outfile) and os.path.getsize(outfile) > 100000:
        sz = os.path.getsize(outfile)/1024/1024
        print(f"  {state}: Already downloaded ({sz:.0f} MB) — skipping")
        return True

    print(f"  {state}: Downloading {len(bbox_list)} tile(s)...")
    all_feats = []

    for i, bbox in enumerate(bbox_list):
        print(f"  Tile {i+1}/{len(bbox_list)}: {bbox}")
        feats = download_bbox(state, bbox, url, where, fields)
        all_feats.extend(feats)
        time.sleep(1)

    # Deduplicate by feature id if present (tiles may overlap slightly)
    seen_ids = set()
    unique_feats = []
    for f in all_feats:
        fid = f.get('id', id(f))
        if fid not in seen_ids:
            seen_ids.add(fid)
            unique_feats.append(f)

    print(f"  {state}: {len(all_feats)} total → {len(unique_feats)} unique after dedup")

    with open(outfile, 'w') as fp:
        json.dump({'type': 'FeatureCollection', 'features': unique_feats}, fp)
    sz = os.path.getsize(outfile)/1024/1024
    print(f"  {state}: DONE — {len(unique_feats)} features, {sz:.0f} MB → {outfile}")
    return True

print("=== NFHL Retry — Failed States (sub-tile approach) ===")
print(f"Target states: {list(RETRY_STATES.keys())}")
print()

for state, bbox_list in RETRY_STATES.items():
    print(f"\n--- {state} ---")
    sfha_out = f"{OUT_DIR}/nfhl_sfha_{state.lower()}.geojson"
    download_state(state, bbox_list, QUERY, SFHA_WHERE, sfha_out)

print("\n=== Also downloading availability (Layer 0) for all 7 states ===")
AVAIL_STATES = {
    'AZ': ['-115.2,30.8,-108.8,37.7'],
    'IL': ['-91.7,36.7,-86.8,42.7'],
    'IA': ['-97.0,40.1,-90.0,43.8'],
    'OR': ['-125.0,41.7,-116.2,46.5'],
    'TX': ['-107.0,25.6,-102.0,36.7', '-102.0,25.6,-93.3,36.7'],
    'VA': ['-84.0,36.3,-75.0,39.7'],
    'WV': ['-83.0,37.0,-77.5,40.8'],
}

for state, bbox_list in AVAIL_STATES.items():
    print(f"\n--- {state} availability ---")
    avail_out = f"{OUT_DIR}/nfhl_avail_{state.lower()}.geojson"
    if os.path.exists(avail_out) and os.path.getsize(avail_out) > 1000:
        print(f"  {state} avail: already done")
        continue
    download_state(state, bbox_list, AVAIL_Q, "1=1", avail_out, fields='SHAPE')

print("\n=== Retry complete ===")
import os
for f in sorted(os.listdir(OUT_DIR)):
    path = f"{OUT_DIR}/{f}"
    sz = os.path.getsize(path)/1024/1024
    status = "✅" if sz > 0.1 else "❌ EMPTY"
    print(f"  {status} {f}: {sz:.1f} MB")
