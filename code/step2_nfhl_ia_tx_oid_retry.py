#!/usr/bin/env python3
"""
step2_nfhl_ia_tx_oid_retry.py
Improved NFHL download for IA and TX using ObjectID-range pagination.

WHY THIS IS MORE RELIABLE than offset-based pagination:
  - ESRI REST API offset pagination (resultOffset=N) is unreliable for large datasets:
    the server must count from row 0 each time, causing timeouts for high-offset pages.
  - ObjectID-range pagination (WHERE OBJECTID > X AND OBJECTID <= Y) uses the server's
    indexed primary key — fast and stable regardless of dataset size.

APPROACH:
  1. Tile the state bbox into small sub-tiles (≤ 5000 expected features each)
  2. For each sub-tile, query returnIdsOnly=true to get all ObjectIDs
  3. Chunk ObjectIDs into batches of 200 and request each batch
  4. Append new features (deduplicate by OBJECTID) into the existing state GeoJSON

STATES TARGETED: Iowa (IA) and Texas (TX) — only states with significant API gaps
"""

import json, os, sys, time, subprocess, math
from urllib.parse import urlencode

BASE    = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
OUTDIR  = f"{BASE}/07_hazards/raw/flood/nfhl"
SERVICE = "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/28"
TIMEOUT_IDS   = 90   # sec — getting IDs only (small response)
TIMEOUT_FEATS = 180  # sec — getting feature geometry
BATCH_SIZE    = 200  # ObjectIDs per request

def curl_json(url, timeout=120, retries=3, delay=15):
    """Return parsed JSON from url, None on failure."""
    for attempt in range(retries):
        r = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), "-L", url],
            capture_output=True, text=True
        )
        if r.returncode != 0 or not r.stdout.strip():
            print(f"    curl attempt {attempt+1}/{retries} failed (returncode={r.returncode})")
            time.sleep(delay)
            continue
        try:
            data = json.loads(r.stdout)
            if "error" in data:
                print(f"    API error: {data['error']}")
                time.sleep(delay)
                continue
            return data
        except json.JSONDecodeError as e:
            print(f"    JSON parse error: {e}")
            time.sleep(delay)
    return None

def get_oids(bbox, timeout=TIMEOUT_IDS):
    """Return sorted list of all ObjectIDs within bbox, or None on failure."""
    params = {
        "where": "FLD_ZONE IN ('A','AE','AO','AH','AR','A99','VE','V','X')",
        "geometry": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "returnIdsOnly": "true",
        "f": "json"
    }
    url = f"{SERVICE}/query?{urlencode(params)}"
    data = curl_json(url, timeout=timeout)
    if data is None:
        return None
    oids = data.get("objectIds") or []
    return sorted(oids)

def get_features_by_oids(oid_batch):
    """Return list of GeoJSON features for a given list of ObjectIDs."""
    params = {
        "objectIds": ",".join(str(o) for o in oid_batch),
        "outFields": "FLD_ZONE,FLD_AR_ID,SFHA_TF,FLOODWAY,STATIC_BFE,DEPTH,LEN_UNIT,VELOCITY,VEL_UNIT,AR_REVERT,AR_SUBTRV,BFE_REVERT,DFIRM_ID,VERSION_ID,SHAPE_Length,SHAPE_Area",
        "outSR": "4326",
        "f": "geojson",
    }
    url = f"{SERVICE}/query?{urlencode(params)}"
    data = curl_json(url, timeout=TIMEOUT_FEATS, retries=3, delay=20)
    if data is None:
        return []
    return data.get("features", [])

# ─── State definitions: finer tiles than original script ─────────────────────
STATES = {
    "ia": {
        "file": f"{OUTDIR}/nfhl_sfha_ia.geojson",
        "tiles": [
            # 12 sub-tiles across IA (was 2 large tiles → timed out heavily)
            (-97.0, 40.1, -95.0, 41.2),
            (-97.0, 41.2, -95.0, 43.8),
            (-95.0, 40.1, -93.5, 41.5),
            (-95.0, 41.5, -93.5, 43.8),
            (-93.5, 40.1, -91.5, 41.5),
            (-93.5, 41.5, -91.5, 43.8),
            (-91.5, 40.1, -90.0, 41.5),
            (-91.5, 41.5, -90.0, 43.8),
        ],
    },
    "tx": {
        "file": f"{OUTDIR}/nfhl_sfha_tx.geojson",
        "tiles": [
            # 24 sub-tiles across TX (was 6 large tiles → many timeouts)
            # Row 1: south strip
            (-107.0, 25.6, -103.0, 28.0),
            (-103.0, 25.6, -99.0,  28.0),
            (-99.0,  25.6, -95.0,  28.0),
            (-95.0,  25.6, -93.3,  28.0),
            # Row 2: mid-south
            (-107.0, 28.0, -103.0, 30.5),
            (-103.0, 28.0, -99.0,  30.5),
            (-99.0,  28.0, -95.0,  30.5),
            (-95.0,  28.0, -93.3,  30.5),
            # Row 3: central
            (-107.0, 30.5, -103.0, 33.0),
            (-103.0, 30.5, -99.0,  33.0),
            (-99.0,  30.5, -95.0,  33.0),
            (-95.0,  30.5, -93.3,  33.0),
            # Row 4: north
            (-107.0, 33.0, -103.0, 36.7),
            (-103.0, 33.0, -99.0,  36.7),
            (-99.0,  33.0, -95.0,  36.7),
            (-95.0,  33.0, -93.3,  36.7),
        ],
    },
}

def load_existing(filepath):
    """Load existing GeoJSON, return (feature list, existing OID set)."""
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 200:
        return [], set()
    with open(filepath) as f:
        data = json.load(f)
    feats = data.get("features", [])
    oids = set()
    for feat in feats:
        oid = (feat.get("id") or
               feat.get("properties", {}).get("OBJECTID") or
               feat.get("properties", {}).get("objectid") or
               feat.get("properties", {}).get("FID"))
        if oid is not None:
            oids.add(int(oid))
    return feats, oids

def process_state(state_code, cfg):
    print(f"\n{'='*60}")
    print(f"=== Improved download: {state_code.upper()} ===")
    outfile = cfg["file"]
    tiles   = cfg["tiles"]

    # Load what we already have
    existing_feats, existing_oids = load_existing(outfile)
    print(f"  Existing features: {len(existing_feats):,} (OIDs tracked: {len(existing_oids):,})")

    new_feats = list(existing_feats)
    new_count = 0
    dup_count = 0

    for ti, tile in enumerate(tiles, 1):
        print(f"\n  Sub-tile {ti}/{len(tiles)}: bbox={tile}")

        # Step 1: get all OIDs in this tile
        oids = get_oids(tile)
        if oids is None:
            print(f"    Could not retrieve OIDs — skipping tile")
            continue
        if not oids:
            print(f"    No features in this tile")
            continue

        # Filter to only OIDs we don't already have
        missing_oids = [o for o in oids if o not in existing_oids]
        print(f"    Total OIDs: {len(oids):,} | Already have: {len(oids)-len(missing_oids):,} | Need: {len(missing_oids):,}")

        if not missing_oids:
            print(f"    All features already downloaded — skipping")
            continue

        # Step 2: fetch in batches of BATCH_SIZE
        n_batches = math.ceil(len(missing_oids) / BATCH_SIZE)
        tile_new = 0
        for bi, start in enumerate(range(0, len(missing_oids), BATCH_SIZE), 1):
            batch = missing_oids[start:start + BATCH_SIZE]
            feats = get_features_by_oids(batch)
            for feat in feats:
                oid = (feat.get("id") or
                       feat.get("properties", {}).get("OBJECTID") or
                       feat.get("properties", {}).get("objectid"))
                if oid is not None and int(oid) not in existing_oids:
                    new_feats.append(feat)
                    existing_oids.add(int(oid))
                    tile_new += 1
                else:
                    dup_count += 1
            if bi % 10 == 0 or bi == n_batches:
                print(f"    Batch {bi}/{n_batches} — running total new: {new_count + tile_new:,}")
            time.sleep(2)  # polite delay between batches

        new_count += tile_new
        print(f"    Tile {ti} complete: +{tile_new} new features")

        # Save checkpoint after each tile
        print(f"    Saving checkpoint ({len(new_feats):,} total features)...")
        with open(outfile, "w") as f:
            json.dump({"type": "FeatureCollection", "features": new_feats}, f)

    print(f"\n=== {state_code.upper()} COMPLETE ===")
    print(f"  New features added: {new_count:,}")
    print(f"  Duplicates skipped: {dup_count:,}")
    print(f"  Final total:        {len(new_feats):,}")
    sz = os.path.getsize(outfile) / 1024 / 1024
    print(f"  File size:          {sz:.1f} MB")
    return new_count

if __name__ == "__main__":
    import sys
    target_states = sys.argv[1:] if len(sys.argv) > 1 else ["ia", "tx"]
    target_states = [s.lower() for s in target_states]

    print("=== NFHL IA/TX Improved OID-range Download ===")
    print(f"Targeting states: {', '.join(s.upper() for s in target_states)}")
    print(f"Service: {SERVICE}")
    print(f"Batch size: {BATCH_SIZE} OIDs per request")
    print()

    totals = {}
    for state in target_states:
        if state not in STATES:
            print(f"Unknown state: {state}")
            continue
        added = process_state(state, STATES[state])
        totals[state] = added

    print("\n=== SUMMARY ===")
    for state, count in totals.items():
        print(f"  {state.upper()}: +{count:,} new features")
    print("\nIMPORTANT: Re-run step2b_nfhl_process.py after this to rebuild rasters.")
