"""
NEXUS Data Center Site Selection — Master Data Downloader
=========================================================
Run this script from your project root. All files land in ./data/<category>/

Requirements:
    pip install requests tqdm

Usage:
    python nexus_download_all.py

    # Download only specific categories:
    python nexus_download_all.py --only boundaries power hazard

    # Skip specific categories:
    python nexus_download_all.py --skip community cost

Categories:
    boundaries, power, hazard, permits_ej, community, cost, carbon
"""

import argparse
import os
import sys
import time
import zipfile
import io
from pathlib import Path

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("Missing dependencies. Run:  pip install requests tqdm")
    sys.exit(1)


# ─── Output directory ──────────────────────────────────────────────────────────
BASE_DIR = Path("./data")

# ─── Color helpers ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✓{RESET}  {msg}")
def warn(msg):  print(f"  {YELLOW}⚠{RESET}  {msg}")
def err(msg):   print(f"  {RED}✗{RESET}  {msg}")
def info(msg):  print(f"  {CYAN}→{RESET}  {msg}")
def head(msg):  print(f"\n{BOLD}{msg}{RESET}")


# ─── Core download function ────────────────────────────────────────────────────
def download(url, dest: Path, label: str = "", unzip: bool = False,
             chunk_size: int = 1024 * 512, retries: int = 3) -> bool:
    """
    Download url → dest. If unzip=True, extract ZIP contents into dest.parent.
    Returns True on success.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and dest.stat().st_size > 0:
        ok(f"{label or dest.name}  {YELLOW}(already downloaded, skipping){RESET}")
        return True

    for attempt in range(1, retries + 1):
        try:
            info(f"Downloading {label or dest.name} …")
            r = requests.get(url, stream=True, timeout=120,
                             headers={"User-Agent": "NEXUS-DataDownloader/1.0"})
            r.raise_for_status()

            total = int(r.headers.get("content-length", 0))
            buf = io.BytesIO()

            with tqdm(total=total, unit="B", unit_scale=True,
                      desc=f"    {dest.name[:45]}", leave=False) as pbar:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    buf.write(chunk)
                    pbar.update(len(chunk))

            buf.seek(0)

            if unzip:
                info("Extracting ZIP …")
                with zipfile.ZipFile(buf) as zf:
                    zf.extractall(dest.parent)
                # Write a sentinel so we know it succeeded
                dest.touch()
            else:
                dest.write_bytes(buf.read())

            ok(f"{label or dest.name}")
            return True

        except Exception as e:
            if attempt < retries:
                wait = 2 ** attempt
                warn(f"Attempt {attempt} failed ({e}). Retrying in {wait}s …")
                time.sleep(wait)
            else:
                err(f"Failed after {retries} attempts: {label or dest.name}\n      URL: {url}\n      Error: {e}")
                return False


def manual(label: str, url: str, notes: str = ""):
    """Print instructions for datasets that require a browser / login."""
    print(f"  {YELLOW}[MANUAL]{RESET}  {BOLD}{label}{RESET}")
    print(f"           URL:   {url}")
    if notes:
        print(f"           Note:  {notes}")


# ══════════════════════════════════════════════════════════════════════════════
# DATASET DEFINITIONS
# Each function downloads one category and returns (success_count, fail_count).
# ══════════════════════════════════════════════════════════════════════════════

def download_boundaries():
    head("1 / 7  BOUNDARIES")
    d = BASE_DIR / "boundaries"
    results = []

    # Natural Earth — 1:10m cultural vectors (countries, states/provinces)
    results.append(download(
        "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip",
        d / "ne_10m_admin_0_countries.zip",
        label="Natural Earth — Countries (1:10m)",
        unzip=True
    ))
    results.append(download(
        "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip",
        d / "ne_10m_admin_1_states_provinces.zip",
        label="Natural Earth — States/Provinces (1:10m)",
        unzip=True
    ))

    # US Census TIGER — States (simple/cartographic)
    results.append(download(
        "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_500k.zip",
        d / "census_states_500k.zip",
        label="Census TIGER — US States 500k",
        unzip=True
    ))
    # US Census TIGER — Counties
    results.append(download(
        "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip",
        d / "census_counties_500k.zip",
        label="Census TIGER — US Counties 500k",
        unzip=True
    ))

    s, f = results.count(True), results.count(False)
    print(f"\n  Boundaries: {s} succeeded, {f} failed")
    return s, f


def download_power():
    head("2 / 7  POWER INFRASTRUCTURE  (HIFLD + EIA)")
    d = BASE_DIR / "power"
    results = []

    # HIFLD — Electric Transmission Lines (ArcGIS Open Data)
    results.append(download(
        "https://opendata.arcgis.com/datasets/70512b03fe994c6393107cc9946e5c22_0.geojson",
        d / "hifld_transmission_lines.geojson",
        label="HIFLD — Electric Transmission Lines (GeoJSON)"
    ))

    # HIFLD — Electric Substations
    results.append(download(
        "https://opendata.arcgis.com/datasets/ebe3ae7f76954aba97d1b5b7687dde43_0.geojson",
        d / "hifld_electric_substations.geojson",
        label="HIFLD — Electric Substations (GeoJSON)"
    ))

    # HIFLD — Natural Gas Pipelines (relevant for generator backup)
    results.append(download(
        "https://opendata.arcgis.com/datasets/f7f811a1fd6b48d0a01523d45e2e543b_0.geojson",
        d / "hifld_natural_gas_pipelines.geojson",
        label="HIFLD — Natural Gas Pipelines (GeoJSON)"
    ))

    # EIA — Utility service territories
    results.append(download(
        "https://opendata.arcgis.com/datasets/f4cd55044b924fed9bc8b64022966097_0.geojson",
        d / "eia_utility_service_territories.geojson",
        label="EIA — Utility Service Territories (GeoJSON)"
    ))

    # EIA Form 861 — Average retail electricity rates by utility (latest year)
    results.append(download(
        "https://www.eia.gov/electricity/data/eia861/zip/f8612023.zip",
        d / "eia861_2023.zip",
        label="EIA Form 861 — 2023 Retail Rates (ZIP, contains XLSX)",
        unzip=True
    ))

    # Manual: FERC Interconnection Queue (requires browser navigation)
    manual(
        "FERC Interconnection Queue",
        "https://www.ferc.gov/industries-data/electric/electric-power-markets/interconnection-queues",
        "Select your ISO/RTO (e.g. PJM, MISO, SPP) → download active queue CSV"
    )

    s, f = results.count(True), results.count(False)
    print(f"\n  Power: {s} succeeded, {f} failed")
    return s, f


def download_hazard():
    head("3 / 7  HAZARD & RISK")
    d = BASE_DIR / "hazard"
    results = []

    # FEMA National Risk Index — county-level (CSV + shapefile)
    results.append(download(
        "https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload//NRI_Table_Counties/NRI_Table_Counties.zip",
        d / "fema_nri_counties.zip",
        label="FEMA NRI — County Risk Index (ZIP)",
        unzip=True
    ))

    # FEMA NRI — Census Tract level (more granular)
    results.append(download(
        "https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload//NRI_Table_CensusTracts/NRI_Table_CensusTracts.zip",
        d / "fema_nri_tracts.zip",
        label="FEMA NRI — Census Tract Risk Index (ZIP)",
        unzip=True
    ))

    # USGS Seismic Hazard — Peak Ground Acceleration (2% in 50yr) — GeoTIFF
    results.append(download(
        "https://earthquake.usgs.gov/static/lfs/nshm/conterminous/2018/hazard/pga2pct50yr.zip",
        d / "usgs_seismic_pga_2pct50yr.zip",
        label="USGS — Seismic PGA 2%/50yr (GeoTIFF ZIP)",
        unzip=True
    ))

    # NOAA Storm Events — latest available year (2023)
    for part in range(1, 4):
        results.append(download(
            f"https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_details-ftp_v1.0_d2023_c20240716.csv.gz",
            d / f"noaa_storm_events_2023.csv.gz",
            label=f"NOAA Storm Events — 2023 Details"
        ))
        break  # single file, loop just for clarity

    # FEMA NFHL (Flood) — national layer via ArcGIS REST (GeoJSON bbox approach)
    # Note: full NFHL is too large to download as one file; point to the WMS/tile service
    manual(
        "FEMA NFHL — 100/500yr Floodplains",
        "https://msc.fema.gov/portal/availabilitySearch",
        "Select by state/county. For programmatic access use the NFHL WMS: "
        "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHLOS/MapServer"
    )

    s, f = results.count(True), results.count(False)
    print(f"\n  Hazard: {s} succeeded, {f} failed")
    return s, f


def download_permits_ej():
    head("4 / 7  PERMITS & ENVIRONMENTAL JUSTICE")
    d = BASE_DIR / "permits_ej"
    results = []

    # EPA EJScreen — Block Group level (full national GDB or CSV)
    results.append(download(
        "https://gaftp.epa.gov/EJSCREEN/2023/EJSCREEN_2023_BG_with_AS_CNMI_GU_VI_Percentiles_csv.zip",
        d / "ejscreen_2023_bg.zip",
        label="EPA EJScreen 2023 — Block Group CSV (full national)",
        unzip=True
    ))

    # EPA EJScreen — Shapefile version
    results.append(download(
        "https://gaftp.epa.gov/EJSCREEN/2023/EJSCREEN_2023_BG_StatePct_with_AS_CNMI_GU_VI_Percentiles_Shapefile.zip",
        d / "ejscreen_2023_shp.zip",
        label="EPA EJScreen 2023 — Block Group Shapefile",
        unzip=True
    ))

    # DOE Energy Communities — coal/fossil-fuel communities (IRA adders eligibility)
    results.append(download(
        "https://edx.netl.doe.gov/api/3/action/resource_download?id=979dc361-19f6-4fd2-a92b-74dc20e7f0b3",
        d / "doe_energy_communities.zip",
        label="DOE Energy Communities (IRA adders) — Shapefile ZIP",
        unzip=True
    ))

    # Opportunity Zones — US Treasury / CDFI Fund
    results.append(download(
        "https://www.cdfifund.gov/sites/cdfi/files/2023-12/Designated_QOZ_12.28.2023.xlsx",
        d / "opportunity_zones_2023.xlsx",
        label="Treasury — Designated Opportunity Zones (XLSX)"
    ))

    # Army Corps Wetlands — NWI (National Wetlands Inventory) via FWS
    manual(
        "USFWS National Wetlands Inventory",
        "https://www.fws.gov/program/national-wetlands-inventory/download-state-wetlands-data",
        "Download by state as shapefile. Large files — download only target states."
    )

    # EPA ECHO — Facility-level permits
    manual(
        "EPA ECHO — Permit Data",
        "https://echo.epa.gov/tools/data-downloads",
        "Download ICIS-Air, NPDES, or RCRA facility CSVs. Filter by state post-download."
    )

    s, f = results.count(True), results.count(False)
    print(f"\n  Permits/EJ: {s} succeeded, {f} failed")
    return s, f


def download_community():
    head("5 / 7  COMMUNITY & DEMOGRAPHICS")
    d = BASE_DIR / "community"
    results = []

    # CDC SVI — Social Vulnerability Index 2022 (county + tract)
    results.append(download(
        "https://www.atsdr.cdc.gov/placeandhealth/svi/data_documentation_download.html",
        d / "cdc_svi_note.txt",
        label="CDC SVI — Note (download page, see below)"
    ))
    # Direct CSV links for SVI 2022
    for geo, slug in [("county", "County"), ("tract", "Tract")]:
        results.append(download(
            f"https://svi.cdc.gov/Documents/Data/2022_SVI_Data/CSV/{slug}/SVI2022_US_{slug.upper()}.csv",
            d / f"cdc_svi_2022_{geo}.csv",
            label=f"CDC SVI 2022 — US {slug}"
        ))

    # Census ACS 5yr — Summary data via Census API (key variables)
    # Writing a helper script instead of raw download (requires API key for full access)
    acs_script = BASE_DIR / "community" / "fetch_acs.py"
    acs_script.parent.mkdir(parents=True, exist_ok=True)
    acs_script.write_text("""\
\"\"\"
Fetch ACS 5-Year estimates for key data center siting variables.
Requires a free Census API key: https://api.census.gov/data/key_signup.html

Variables fetched (county level):
  B19013_001E  Median household income
  B01003_001E  Total population
  B08301_001E  Total commuters (labor market proxy)
  B25001_001E  Total housing units (density proxy)
  B23025_005E  Unemployed (labor availability)
\"\"\"
import requests, csv, os

API_KEY = os.environ.get("CENSUS_API_KEY", "YOUR_KEY_HERE")
YEAR    = "2022"
VARS    = "B19013_001E,B01003_001E,B08301_001E,B25001_001E,B23025_005E"
URL     = f"https://api.census.gov/data/{YEAR}/acs/acs5?get=NAME,{VARS}&for=county:*&key={API_KEY}"

r = requests.get(URL, timeout=60)
r.raise_for_status()
rows = r.json()

with open("acs5_county_siting_vars.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)
print(f"Saved {len(rows)-1} counties to acs5_county_siting_vars.csv")
""")
    ok("Census ACS helper script written → data/community/fetch_acs.py")
    ok("  (add your free Census API key and run it separately)")

    s, f = results.count(True), results.count(False)
    print(f"\n  Community: {s} succeeded, {f} failed")
    return s, f


def download_cost():
    head("6 / 7  COST PROXIES")
    d = BASE_DIR / "cost"
    results = []

    # BLS OEWS — Occupational Employment & Wages (all industries, national + state)
    results.append(download(
        "https://www.bls.gov/oes/special.requests/oesm23all.zip",
        d / "bls_oews_2023_all.zip",
        label="BLS OEWS 2023 — All Industries All Areas (ZIP)",
        unzip=True
    ))

    # EIA — State-level average retail electricity prices (monthly, all sectors)
    results.append(download(
        "https://www.eia.gov/electricity/data/browser/csv.php?chart_type=column&linechart=ELEC.PRICE.US-ALL.M&columnchart=ELEC.PRICE.US-ALL.M&map_active=1&map_statecode=US",
        d / "eia_retail_electricity_prices.csv",
        label="EIA — Retail Electricity Prices by State/Sector (CSV)"
    ))

    # EIA Electric Power Monthly — Table 5.6.A (average retail price by state)
    results.append(download(
        "https://www.eia.gov/electricity/monthly/xls/table_5_06_a.xlsx",
        d / "eia_avg_retail_price_by_state.xlsx",
        label="EIA — Average Retail Electricity Price by State (XLSX)"
    ))

    # Good Jobs First — Subsidy Tracker (bulk download)
    results.append(download(
        "https://subsidytracker.goodjobsfirst.org/prog.php?parent=&detail=all&state=&subsidy_type=&date_from=&date_to=&award_lt=&award_gt=100000000&wage_flag=&job_flag=&format=csv",
        d / "good_jobs_first_subsidies_100M_plus.csv",
        label="Good Jobs First — Subsidies >$100M (CSV)"
    ))

    # Manual entries
    manual(
        "Regrid Parcel Data (land values)",
        "https://regrid.com/plans",
        "Freemium. Download by county. Essential for site-level land cost estimates."
    )
    manual(
        "RSMeans City Cost Index",
        "https://www.rsmeansonline.com",
        "Commercial. County-level construction cost multipliers. ~$300/yr academic pricing available."
    )
    manual(
        "CoStar / LoopNet — Industrial land comps",
        "https://www.loopnet.com",
        "Manual research per market. Pull $/sqft for industrial/data center-zoned parcels."
    )

    s, f = results.count(True), results.count(False)
    print(f"\n  Cost: {s} succeeded, {f} failed")
    return s, f


def download_carbon():
    head("7 / 7  CARBON & ENERGY (supplement to your existing data)")
    d = BASE_DIR / "carbon"
    results = []

    # EPA eGRID — Grid emissions by subregion (most recent = 2022)
    results.append(download(
        "https://www.epa.gov/system/files/documents/2024-01/egrid2022_data.xlsx",
        d / "epa_egrid_2022.xlsx",
        label="EPA eGRID 2022 — Grid Emissions by Subregion (XLSX)"
    ))

    # EPA eGRID Shapefiles — subregion boundaries to join with eGRID data
    results.append(download(
        "https://www.epa.gov/system/files/documents/2024-01/egrid2022_subregions_shapefile.zip",
        d / "epa_egrid_2022_subregions.zip",
        label="EPA eGRID 2022 — Subregion Shapefile",
        unzip=True
    ))

    # EIA — Hourly Grid Monitor (BA-level carbon intensity supplement)
    manual(
        "EIA Hourly Electric Grid Monitor",
        "https://www.eia.gov/electricity/gridmonitor/dashboard/electric_overview/US48/US48",
        "Download bulk CSV via the API endpoint: "
        "https://api.eia.gov/bulk/EBA.zip  (requires free API key)"
    )

    # WattTime / ElectricityMaps — marginal emissions by BA (if not already covered)
    manual(
        "ElectricityMaps — Marginal Carbon Intensity",
        "https://api.electricitymap.org",
        "Free academic tier available. Provides real-time + historical marginal intensity by zone."
    )

    s, f = results.count(True), results.count(False)
    print(f"\n  Carbon: {s} succeeded, {f} failed")
    return s, f


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

CATEGORY_MAP = {
    "boundaries": download_boundaries,
    "power":      download_power,
    "hazard":     download_hazard,
    "permits_ej": download_permits_ej,
    "community":  download_community,
    "cost":       download_cost,
    "carbon":     download_carbon,
}

def main():
    parser = argparse.ArgumentParser(description="NEXUS master data downloader")
    parser.add_argument("--only", nargs="+", choices=CATEGORY_MAP.keys(), metavar="CAT",
                        help="Download only these categories")
    parser.add_argument("--skip", nargs="+", choices=CATEGORY_MAP.keys(), metavar="CAT",
                        help="Skip these categories")
    args = parser.parse_args()

    categories = list(CATEGORY_MAP.keys())
    if args.only:
        categories = [c for c in categories if c in args.only]
    if args.skip:
        categories = [c for c in categories if c not in args.skip]

    print(f"\n{BOLD}{'═'*60}")
    print(f"  NEXUS Data Center Site Selection — Master Downloader")
    print(f"  Output root: {BASE_DIR.resolve()}")
    print(f"  Categories:  {', '.join(categories)}")
    print(f"{'═'*60}{RESET}")

    total_s, total_f = 0, 0
    for cat in categories:
        s, f = CATEGORY_MAP[cat]()
        total_s += s
        total_f += f

    print(f"\n{BOLD}{'═'*60}")
    print(f"  DONE  —  {GREEN}{total_s} succeeded{RESET}{BOLD},  "
          f"{RED if total_f else ''}{total_f} failed{RESET}")
    print(f"{'═'*60}{RESET}\n")

    if total_f:
        print(f"{YELLOW}Failed downloads are usually due to rate limits or URL changes.")
        print(f"Re-run the script — it skips already-downloaded files.{RESET}\n")


if __name__ == "__main__":
    main()
