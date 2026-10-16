#!/usr/bin/env python3
"""
Step 2: Download NFHL SFHA + Availability zones via FEMA ArcGIS REST API.
Uses paginated POST requests with SFHA_TF='T' filter per state bounding box.
"""
import subprocess, json, os, time

OUT_DIR = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/07_hazards/raw/flood/nfhl"
os.makedirs(OUT_DIR, exist_ok=True)

BASE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
L28  = f"{BASE}/28/query"   # Flood Hazard Zones
L0   = f"{BASE}/0/query"    # NFHL Availability (coverage QA)

# 7-state bounding boxes (WGS84: minx,miny,maxx,maxy with 0.2° buffer)
STATES = {
    'AZ': '-115.2,30.8,-108.8,37.7',
    'IL': '-91.7,36.7,-86.8,42.7',
    'IA': '-97.0,40.1,-90.0,43.8',
    'OR': '-125.0,41.7,-116.2,46.5',
    'TX': '-107.0,25.6,-93.3,36.7',
    'VA': '-84.0,36.3,-75.0,39.7',
    'WV': '-83.0,37.0,-77.5,40.8',
}

SFHA_ZONES = "('A','AE','AO','AH','AR','A99','VE','V')"

def query_page(url, params, timeout=60):
    """POST a page query and return parsed JSON."""
    import urllib.parse
    data = urllib.parse.urlencode(params).encode()
    result = subprocess.run(
        ['curl', '-sk', '--max-time', str(timeout), '-X', 'POST', '--data', data.decode(), url],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

def get_count(url, where, bbox):
    d = query_page(url, {
        'where': where,
        'geometry': bbox,
        'geometryType': 'esriGeometryEnvelope',
        'spatialRel': 'esriSpatialRelIntersects',
        'returnCountOnly': 'true',
        'f': 'json'
    })
    return d.get('count', 0) if d else 0

def download_features(url, where, bbox, out_geojson, outfields='*', page_size=2000):
    """Download all features matching query to GeoJSON file."""
    count = get_count(url, where, bbox)
    print(f"    Total records: {count}")
    
    all_features = []
    offset = 0
    while True:
        d = query_page(url, {
            'where': where,
            'geometry': bbox,
            'geometryType': 'esriGeometryEnvelope',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': outfields,
            'resultRecordCount': page_size,
            'resultOffset': offset,
            'outSR': '4326',
            'f': 'geojson'
        })
        if d is None:
            print(f"    ERROR at offset {offset}, retrying...")
            time.sleep(3)
            d = query_page(url, {
                'where': where,
                'geometry': bbox,
                'geometryType': 'esriGeometryEnvelope',
                'spatialRel': 'esriSpatialRelIntersects',
                'outFields': outfields,
                'resultRecordCount': page_size,
                'resultOffset': offset,
                'outSR': '4326',
                'f': 'geojson'
            })
            if d is None:
                print(f"    FAILED at offset {offset}, skipping page")
                offset += page_size
                continue
        
        feats = d.get('features', [])
        if not feats:
            break
        all_features.extend(feats)
        exceeded = d.get('exceededTransferLimit', False)
        print(f"    Page offset {offset}: {len(feats)} features (total so far: {len(all_features)})")
        
        if not exceeded or len(feats) < page_size:
            break
        offset += page_size
        time.sleep(0.5)  # Be polite
    
    # Save as GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': all_features
    }
    with open(out_geojson, 'w') as f:
        json.dump(geojson, f)
    print(f"    Saved {len(all_features)} features → {out_geojson}")
    return len(all_features)

# Download SFHA zones per state
print("=== Downloading NFHL Layer 28 — SFHA Zones ===")
total_features = 0
for state, bbox in STATES.items():
    print(f"\n--- {state} ---")
    out = f"{OUT_DIR}/nfhl_sfha_{state.lower()}.geojson"
    n = download_features(
        L28,
        where=f"FLD_ZONE IN {SFHA_ZONES}",
        bbox=bbox,
        out_geojson=out,
        outfields='FLD_ZONE,ZONE_SUBTY,SFHA_TF',
    )
    total_features += n

print(f"\nTotal SFHA features downloaded: {total_features}")

# Download NFHL Availability (Layer 0) per state — for coverage QA
print("\n=== Downloading NFHL Layer 0 — Availability ===")
for state, bbox in STATES.items():
    print(f"\n--- {state} ---")
    out = f"{OUT_DIR}/nfhl_avail_{state.lower()}.geojson"
    download_features(
        L0,
        where="1=1",
        bbox=bbox,
        out_geojson=out,
        outfields='*',
    )

print("\n=== NFHL Download complete ===")
print(f"Output directory: {OUT_DIR}")
import os
for f in sorted(os.listdir(OUT_DIR)):
    path = f"{OUT_DIR}/{f}"
    print(f"  {f}: {os.path.getsize(path)/1024/1024:.1f} MB")
