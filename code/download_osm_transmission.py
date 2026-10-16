"""
Download OSM power=line features for 7 study states via Overpass API.
One request per state (bounding box), merge to single GeoJSON.
Output: 02_power_grid/raw/transmission_lines_osm/osm_transmission_7states.geojson
"""

import json
import subprocess
import time
import urllib.parse
from pathlib import Path
from collections import Counter

OUT_DIR = Path(__file__).parent.parent / "02_power_grid" / "raw" / "transmission_lines_osm"
OUT_FILE = OUT_DIR / "osm_transmission_7states.geojson"
META_FILE = OUT_DIR / "osm_transmission_metadata.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# [minLon, minLat, maxLon, maxLat] — used as Overpass (s,w,n,e)
STATE_BOXES = {
    "AZ": (-114.82, 31.33, -109.04, 37.00),
    "IL": (-91.52, 36.97, -87.02, 42.51),
    "IA": (-96.64, 40.38, -90.14, 43.51),
    "OR": (-124.57, 41.99, -116.46, 46.27),
    "TX": (-106.65, 25.84, -93.51, 36.50),
    "VA": (-83.68, 36.54, -75.24, 39.47),
    "WV": (-82.64, 37.20, -77.72, 40.64),
}


def overpass_query(state: str, box) -> str:
    minlon, minlat, maxlon, maxlat = box
    # Overpass bbox order: south,west,north,east
    bbox = f"{minlat},{minlon},{maxlat},{maxlon}"
    return f"""[out:json][timeout:120];
(
  way["power"="line"]({bbox});
);
out geom;"""


def fetch_state(state: str, box) -> list:
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "180", "-A", "dissertation-research/1.0",
                 "--data-urlencode", f"data={overpass_query(state, box)}", OVERPASS_URL],
                capture_output=True, text=True, check=True
            )
            resp = json.loads(result.stdout)
            return resp.get("elements", [])
        except Exception as exc:
            if attempt == 2:
                raise
            print(f"    Retry {attempt+1}: {exc}")
            time.sleep(10)


def way_to_geojson(element: dict, state: str) -> dict | None:
    if element.get("type") != "way":
        return None
    geom = element.get("geometry")
    if not geom:
        return None
    coords = [[pt["lon"], pt["lat"]] for pt in geom]
    tags = element.get("tags", {})
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {
            "osm_id": element.get("id"),
            "state_bbox": state,
            "voltage": tags.get("voltage"),
            "cables": tags.get("cables"),
            "circuits": tags.get("circuits"),
            "frequency": tags.get("frequency"),
            "operator": tags.get("operator"),
            "name": tags.get("name"),
            "power": tags.get("power"),
        }
    }


def main():
    all_features = []
    state_counts = {}
    seen_ids = set()

    for state, box in STATE_BOXES.items():
        print(f"  {state}: querying Overpass ...", end=" ", flush=True)
        elements = fetch_state(state, box)
        features = []
        for el in elements:
            f = way_to_geojson(el, state)
            if f and f["properties"]["osm_id"] not in seen_ids:
                seen_ids.add(f["properties"]["osm_id"])
                features.append(f)
        state_counts[state] = len(features)
        all_features.extend(features)
        print(f"{len(elements)} ways → {len(features)} unique features")
        time.sleep(3)  # be polite to Overpass

    print(f"\nTotal unique OSM power=line features: {len(all_features):,}")

    # Voltage completeness
    has_voltage = sum(1 for f in all_features if f["properties"]["voltage"])
    print(f"Features with voltage tag: {has_voltage:,} / {len(all_features):,} "
          f"({100*has_voltage/len(all_features):.1f}%)")

    # Voltage value distribution
    volt_vals = Counter()
    for f in all_features:
        v = f["properties"]["voltage"]
        if v:
            try:
                kv = float(v.split(";")[0]) / 1000 if ";" in v else float(v) / 1000
                if kv < 100:
                    volt_vals["<100 kV"] += 1
                elif kv < 200:
                    volt_vals["100-199 kV"] += 1
                elif kv < 345:
                    volt_vals["200-344 kV"] += 1
                elif kv < 500:
                    volt_vals["345-499 kV"] += 1
                elif kv < 765:
                    volt_vals["500-764 kV"] += 1
                else:
                    volt_vals["765+ kV"] += 1
            except ValueError:
                volt_vals[f"unparseable: {v}"] += 1
        else:
            volt_vals["MISSING"] += 1
    print("Voltage distribution (kV):")
    for k, v in sorted(volt_vals.items()):
        print(f"  {k:20s}: {v:5,}")

    geojson = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": all_features,
    }
    with open(OUT_FILE, "w") as fh:
        json.dump(geojson, fh)
    print(f"\nSaved → {OUT_FILE}")
    print(f"File size: {OUT_FILE.stat().st_size / 1_048_576:.1f} MB")

    meta = {
        "source": OVERPASS_URL,
        "query": "power=line (way elements only)",
        "access_date": time.strftime("%Y-%m-%d"),
        "states_queried": list(STATE_BOXES.keys()),
        "state_feature_counts": state_counts,
        "total_features": len(all_features),
        "features_with_voltage_tag": has_voltage,
        "voltage_missing_pct": round(100 * (len(all_features) - has_voltage) / len(all_features), 1),
        "voltage_distribution": dict(volt_vals),
        "note": "Bounding-box query — may include lines from adjacent states. Reproject to EPSG:5070 and clip to 7-state boundary before use.",
    }
    with open(META_FILE, "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"Metadata saved → {META_FILE}")


if __name__ == "__main__":
    main()
