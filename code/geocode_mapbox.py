import pandas as pd
import requests
import time
import os

# ----------------------------
# SETTINGS
# ----------------------------
INPUT_FILE = "data_centers_locations.xlsx"
OUTPUT_FILE = "geocoded.csv"

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

if not MAPBOX_TOKEN:
    print("ERROR: No Mapbox token found.")
    print("Run: export MAPBOX_TOKEN='your_token_here'")
    exit()

# ----------------------------
# Load Excel
# ----------------------------
df = pd.read_excel(INPUT_FILE)

print("Rows loaded:", len(df))

# ----------------------------
# Build full address column
# ----------------------------
df["full_address"] = (
    df["address"].astype(str).fillna("") + ", " +
    df["city"].astype(str).fillna("") + ", " +
    df["state"].astype(str).fillna("") + " " +
    df["zip"].astype(str).fillna("")
)

# ----------------------------
# Geocode function
# ----------------------------
def geocode(address):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1}

    r = requests.get(url, params=params)

    if r.status_code != 200:
        return None, None

    data = r.json()

    if len(data["features"]) == 0:
        return None, None

    lon, lat = data["features"][0]["center"]
    return lat, lon

# ----------------------------
# Run geocoding
# ----------------------------
lat_list = []
lon_list = []

for i, addr in enumerate(df["full_address"]):
    addr = str(addr).strip()

    if addr == "" or addr.lower() == "nan":
        lat_list.append(None)
        lon_list.append(None)
        continue

    lat, lon = geocode(addr)

    lat_list.append(lat)
    lon_list.append(lon)

    print(f"{i+1}/{len(df)} done")

    time.sleep(0.1)  # slows down to avoid rate limits

# ----------------------------
# Save output
# ----------------------------
df["latitude"] = lat_list
df["longitude"] = lon_list

df.to_csv(OUTPUT_FILE, index=False)

print("\nDONE!")
print("Saved:", OUTPUT_FILE)
