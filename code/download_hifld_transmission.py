"""
Download fresh HIFLD Electric Power Transmission Lines via ArcGIS FeatureServer.
Service: https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Power_Transmission_Lines/FeatureServer/0
Output: 02_power_grid/raw/transmission_lines_fresh/hifld_transmission_lines_FRESH.geojson
"""

import json
import os
import subprocess
import time
import urllib.parse
from pathlib import Path

BASE_URL = (
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services"
    "/Electric_Power_Transmission_Lines/FeatureServer/0/query"
)
PAGE_SIZE = 2000
OUT_DIR = Path(__file__).parent.parent / "02_power_grid" / "raw" / "transmission_lines_fresh"
OUT_FILE = OUT_DIR / "hifld_transmission_lines_FRESH.geojson"
META_FILE = OUT_DIR / "hifld_transmission_fresh_metadata.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def curl_get(url: str, timeout: int = 120) -> dict:
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", str(timeout), url],
                capture_output=True, text=True, check=True
            )
            return json.loads(result.stdout)
        except Exception as exc:
            if attempt == 2:
                raise
            print(f"  Retry {attempt+1} after error: {exc}")
            time.sleep(5)


def fetch_page(offset: int) -> dict:
    params = urllib.parse.urlencode({
        "where": "1=1",
        "outFields": "*",
        "geometryPrecision": 6,
        "outSR": 4326,
        "f": "geojson",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
    })
    return curl_get(f"{BASE_URL}?{params}")


def main():
    # Get total count
    count_params = urllib.parse.urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"})
    total = curl_get(f"{BASE_URL}?{count_params}")["count"]
    print(f"Total features: {total:,}")

    features = []
    offset = 0
    page = 0

    while offset < total:
        page += 1
        print(f"  Page {page}: offset {offset:,} / {total:,} ...", end=" ", flush=True)
        data = fetch_page(offset)
        batch = data.get("features", [])
        features.extend(batch)
        print(f"{len(batch)} records")
        if not batch or not data.get("exceededTransferLimit", True) and len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.3)

    print(f"\nDownloaded {len(features):,} features total.")

    geojson = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    with open(OUT_FILE, "w") as f:
        json.dump(geojson, f)
    print(f"Saved → {OUT_FILE}")
    print(f"File size: {OUT_FILE.stat().st_size / 1_048_576:.1f} MB")

    # Quick field completeness check
    voltage_missing = sum(
        1 for ft in features
        if ft.get("properties", {}).get("VOLTAGE") in (None, -999999, -999999.0)
    )
    status_counts: dict = {}
    for ft in features:
        s = ft.get("properties", {}).get("STATUS", "NULL")
        status_counts[s] = status_counts.get(s, 0) + 1

    volt_class_counts: dict = {}
    for ft in features:
        vc = ft.get("properties", {}).get("VOLT_CLASS", "NULL")
        volt_class_counts[vc] = volt_class_counts.get(vc, 0) + 1

    meta = {
        "source": BASE_URL,
        "access_date": time.strftime("%Y-%m-%d"),
        "total_features": len(features),
        "voltage_missing_count": voltage_missing,
        "voltage_missing_pct": round(100 * voltage_missing / len(features), 1),
        "status_counts": status_counts,
        "volt_class_counts": volt_class_counts,
        "output_crs": "EPSG:4326",
        "note": "Fresh download. Reproject to EPSG:5070 before use in MCDA.",
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\n--- QC Summary ---")
    print(f"VOLTAGE missing: {voltage_missing:,} / {len(features):,} ({meta['voltage_missing_pct']}%)")
    print(f"STATUS values: {status_counts}")
    print(f"VOLT_CLASS values: {volt_class_counts}")
    print(f"Metadata saved → {META_FILE}")


if __name__ == "__main__":
    main()
