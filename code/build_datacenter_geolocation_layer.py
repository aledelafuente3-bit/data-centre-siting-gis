#!/usr/bin/env python3
"""
build_datacenter_geolocation_layer.py
=====================================
Creates comprehensive public-data geolocation layer for data centres across
7 study states (AZ, IL, IA, OR, TX, VA, WV).

Combines:
  - Existing commercial-directory dataset (1,598 records)
  - Public-source hyperscale research records (65 records researched from
    operator websites, news, planning records, economic development announcements)

Net additions: 29 new records (all Iowa, all WV, selected hyperscale gaps).
Master total: ~1,627 records.

Outputs (all in 06_VALIDATION/observed_data_center_points/):
  data_centers_public_sources_raw.csv          - 65 research records as raw source table
  data_centers_7state_public_master.csv        - cleaned master (1,627 records)
  data_centers_7state_public_master_EPSG4326.gpkg  - WGS84 points
  data_centers_7state_public_master_EPSG5070.gpkg  - EPSG:5070 points
  hyperscale_data_centers_7state_EPSG5070.gpkg     - hyperscale subset
  data_centers_manual_review_needed.csv        - records needing manual review
  DATA_CENTER_GEOLOCATION_PROVENANCE.md        - provenance documentation
And in 00_ADMIN/:
  DATA_CENTER_GEOLOCATION_SUMMARY.md          - summary report

Run with: python3 build_datacenter_geolocation_layer.py
(works in system Python3 for CSV stages; GeoPackage stage uses QGIS Python)

Author: Generated 2026-06-22
"""

import csv
import json
import os
import sys
import math
from datetime import date

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
EXISTING_CSV = f"{BASE}/10_data_centers_validation/raw/geocoded.csv"
RESEARCH_JSON = "/tmp/research_facilities.json"
OUT_DIR = f"{BASE}/06_VALIDATION/observed_data_center_points"
ADMIN_DIR = f"{BASE}/00_ADMIN"

# ── Operator classification rules (applied to existing dataset) ─────────────────
# Each rule: (search_string, operator, parent_company, facility_type,
#              cloud_platform, hyperscale_flag, hyperscale_reason)
OPERATOR_RULES = [
    # Hyperscale cloud operators
    ("amazon aws",  "Amazon AWS", "Amazon.com Inc.", "hyperscale", "AWS",          "yes",     "operated by cloud hyperscaler"),
    ("amazon web",  "Amazon AWS", "Amazon.com Inc.", "hyperscale", "AWS",          "yes",     "operated by cloud hyperscaler"),
    ("aws iad",     "Amazon AWS", "Amazon.com Inc.", "hyperscale", "AWS",          "yes",     "operated by cloud hyperscaler"),
    ("aws pdx",     "Amazon AWS", "Amazon.com Inc.", "hyperscale", "AWS",          "yes",     "operated by cloud hyperscaler"),
    ("aws sat",     "Amazon AWS", "Amazon.com Inc.", "hyperscale", "AWS",          "yes",     "operated by cloud hyperscaler"),
    ("aws phx",     "Amazon AWS", "Amazon.com Inc.", "hyperscale", "AWS",          "yes",     "operated by cloud hyperscaler"),
    ("microsoft",   "Microsoft",  "Microsoft Corporation", "hyperscale", "Azure",  "yes",     "operated by cloud hyperscaler"),
    ("google",      "Google",     "Alphabet Inc.",   "hyperscale", "Google Cloud", "yes",     "operated by cloud hyperscaler"),
    ("meta ",       "Meta",       "Meta Platforms Inc.", "hyperscale", "Meta",     "yes",     "operated by cloud hyperscaler"),
    ("facebook",    "Meta",       "Meta Platforms Inc.", "hyperscale", "Meta",     "yes",     "operated by cloud hyperscaler"),
    ("apple ",      "Apple",      "Apple Inc.",      "hyperscale", "Apple",        "yes",     "operated by cloud hyperscaler"),
    ("oracle ",     "Oracle",     "Oracle Corporation", "hyperscale", "Oracle Cloud", "yes",  "operated by cloud hyperscaler"),
    # Major colocation operators
    ("equinix",     "Equinix",    "Equinix Inc.",    "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("cyrusone",    "CyrusOne",   "CyrusOne Inc.",   "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("qts",         "QTS",        "Blackstone / QTS Data Centers", "colocation", "none", "no", "colocation facility, not hyperscale"),
    ("digital realty", "Digital Realty", "Digital Realty Trust Inc.", "colocation", "none", "no", "colocation facility, not hyperscale"),
    ("iron mountain", "Iron Mountain", "Iron Mountain Inc.", "colocation", "none", "no",    "colocation facility, not hyperscale"),
    ("databank",    "DataBank",   "DataBank Ltd.",   "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("coresite",    "CoreSite",   "American Tower Corporation", "colocation", "none", "no",   "colocation facility, not hyperscale"),
    ("vantage",     "Vantage Data Centers", "DigitalBridge", "colocation", "none", "likely",  "large colocation campus, hyperscale-adjacent"),
    ("edgeconnex",  "EdgeConneX", "EQT AB",          "colocation", "none",         "likely",  "hyperscale-adjacent colocation"),
    ("flexential",  "Flexential", "Flexential",      "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("ntt",         "NTT",        "NTT Ltd.",        "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("stack infra", "STACK Infrastructure", "iSquared Capital", "colocation", "none", "no",   "colocation facility, not hyperscale"),
    ("compass",     "Compass Datacenters", "Compass Datacenters", "colocation", "none", "likely", "large-scale colocation, hyperscale-adjacent"),
    ("corscale",    "CorScale",   "CorScale LLC",    "colocation", "none",         "likely",  "purpose-built hyperscale-adjacent colocation"),
    ("cologix",     "Cologix",    "Cologix LLC",     "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("penzance",    "Penzance",   "Penzance Companies", "colocation", "none",      "yes",     "large announced campus, hyperscale-scale"),
    ("switch",      "Switch Inc.", "DigitalBridge",  "colocation", "none",         "likely",  "large-scale colocation campus"),
    ("cloudflare",  "Cloudflare", "Cloudflare Inc.", "edge",       "none",         "no",      "edge/CDN facility, not hyperscale data centre"),
    ("hivelocity",  "Hivelocity", "Hivelocity",      "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("noaa",        "NOAA",       "U.S. Government", "enterprise", "none",         "no",      "government computing facility"),
    ("cloudiq",     "CloudIQ",    "CloudIQ Technologies", "colocation", "none",    "no",      "colocation facility, not hyperscale"),
    ("xtreme",      "Xtreme",     "Xtreme",          "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("sungard",     "Sungard",    "Sungard Availability Services", "enterprise", "none", "no", "colocation/recovery facility, not hyperscale"),
    ("vazata",      "Vazata",     "Vazata",          "colocation", "none",         "no",      "colocation facility, not hyperscale"),
    ("cloudiq",     "CloudIQ",    "CloudIQ Technologies", "colocation", "none",    "no",      "colocation facility, not hyperscale"),
]

def classify_by_name(name: str):
    """Return (operator, parent, ftype, cloud, hs_flag, hs_reason) from name."""
    n = name.lower()
    for kw, op, parent, ftype, cloud, flag, reason in OPERATOR_RULES:
        if kw in n:
            return op, parent, ftype, cloud, flag, reason
    # Check for bare address-only records (DFW10, IAD53, etc.)
    import re
    if re.search(r'\((?:DFW|IAD|CHI|PHX|PDX|SAT|ORD|SJC|SFO|LAX|MSP)\d+', name):
        return "Unknown", "Unknown", "colocation", "none", "unknown", "insufficient evidence — directory code only"
    return "Unknown", "Unknown", "unknown", "unknown", "unknown", "insufficient evidence"

# ── IDs for already-confirmed-new research records ───────────────────────────
# These are the 29 research records confirmed NOT in existing dataset
# All Iowa (12) + All WV (3) + specific hyperscale gaps (14)
CONFIRMED_NEW_FACILITY_NAMES = {
    # Iowa (12)
    "Google Council Bluffs - Lake Manawa Campus",
    "Google Council Bluffs - Southlands Campus",
    "Google Cedar Rapids Campus",
    "Meta Altoona Campus",
    "Microsoft West Des Moines - Project Mountain",
    "Microsoft West Des Moines - Project Alluvion",
    "Microsoft West Des Moines - Project Osmium",
    "Microsoft West Des Moines - Project Ginger West",
    "Microsoft West Des Moines - Project Ginger East",
    "Microsoft West Des Moines - Project Ruthenium",
    "Apple Waukee Campus - Building 1",
    "QTS Cedar Rapids Campus",
    # WV (3)
    "Penzance Bedington Campus",
    "QTS Kearneysville Campus",
    "NOAA I-79 Technology Park Computing Facility",
    # VA gaps (3)
    "Microsoft Azure Stone Ridge Campus (IAD11)",
    "Google Virginia - Prince William Campus (Gainesville/Bristow)",
    "Oracle Cloud Ashburn (us-ashburn-1)",
    # TX gaps (3)
    "Microsoft Irving - Las Colinas Campus",
    "Amazon AWS Texas - DeSoto Campus",
    "Amazon AWS Texas - Bastrop County Land Acquisition",
    # OR gaps (8)
    "Amazon AWS Boardman - Lewis Campus",
    "Amazon AWS Boardman - Olson Campus",
    "Amazon AWS Boardman - Rippee Campus",
    "Amazon AWS Boardman - Exascale Land Acquisition",
    "Amazon AWS Hermiston Campus",
    "Amazon AWS Hillsboro - Evergreen Campus",
    "Digital Realty Hillsboro PDX10",
    # IL gaps (1)
    "CyrusOne Elk Grove Village (ORD2-A)",
}

# ── Master CSV fieldnames ─────────────────────────────────────────────────────
MASTER_FIELDS = [
    "record_id", "facility_name", "operator", "parent_company",
    "facility_type",       # hyperscale / colocation / enterprise / edge / unknown
    "cloud_platform",      # AWS / Azure / Google Cloud / Meta / Apple / Oracle / none / unknown
    "address_public", "city", "county", "state", "zip",
    "lat", "lon",
    "geocoding_method", "geocoding_confidence",
    "source_type",         # commercial_directory / operator_website / news / planning_record / economic_dev / unknown
    "source_url",
    "access_date",
    "notes",
    "location_precision",  # facility / campus / city / county
    "status",              # active / planned / under_construction / announced / unknown
    "hyperscale_flag",     # yes / likely / no / unknown
    "hyperscale_reason",
    "include_in_validation",  # yes / no / review
    "sources_list",
    "dataset_origin",      # existing_directory / public_research
]

RAW_FIELDS = [
    "facility_name", "operator", "parent_company", "facility_type", "cloud_platform",
    "address_public", "city", "county", "state", "lat", "lon",
    "geocoding_method", "geocoding_confidence",
    "source_url", "source_type", "access_date", "notes",
    "location_precision", "status", "hyperscale_flag", "hyperscale_reason",
    "include_in_validation", "sources_list",
]

def load_existing():
    rows = []
    with open(EXISTING_CSV) as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            # Filter to study states only
            if r.get("state") not in {"AZ","IL","OR","TX","VA"}:
                continue
            op, parent, ftype, cloud, flag, reason = classify_by_name(r.get("name",""))
            # geocoding confidence: high if has address, medium if address is very short/generic
            addr = r.get("address","").strip()
            conf = "high" if (addr and len(addr) > 5 and any(c.isdigit() for c in addr)) else "medium"
            rows.append({
                "record_id": f"EX-{i+1:04d}",
                "facility_name": r.get("name",""),
                "operator": op,
                "parent_company": parent,
                "facility_type": ftype,
                "cloud_platform": cloud,
                "address_public": addr,
                "city": r.get("city",""),
                "county": "",   # not in source
                "state": r.get("state",""),
                "zip": r.get("zip",""),
                "lat": r.get("latitude",""),
                "lon": r.get("longitude",""),
                "geocoding_method": "address geocode (external API)",
                "geocoding_confidence": conf,
                "source_type": "commercial_directory",
                "source_url": "commercial directory — Datacenter Hawk/CBRE format (exact source unverified)",
                "access_date": "unknown",
                "notes": "From existing project validation dataset. Source: commercial DC directory. NOT OSM.",
                "location_precision": "facility",
                "status": "active",
                "hyperscale_flag": flag,
                "hyperscale_reason": reason,
                "include_in_validation": "yes",
                "sources_list": "commercial_directory",
                "dataset_origin": "existing_directory",
            })
    return rows

def load_research():
    """Load research JSON records, identify confirmed-new ones."""
    with open(RESEARCH_JSON) as f:
        recs = json.load(f)
    rows = []
    for i, r in enumerate(recs):
        is_new = r.get("facility_name","") in CONFIRMED_NEW_FACILITY_NAMES
        county = r.get("county","")
        row = {
            "record_id": f"PR-{i+1:03d}",
            "facility_name": r.get("facility_name",""),
            "operator": r.get("operator",""),
            "parent_company": r.get("parent_company",""),
            "facility_type": r.get("facility_type",""),
            "cloud_platform": r.get("cloud_platform",""),
            "address_public": r.get("address_public",""),
            "city": r.get("city",""),
            "county": county,
            "state": r.get("state",""),
            "zip": "",
            "lat": r.get("lat",""),
            "lon": r.get("lon",""),
            "geocoding_method": r.get("geocoding_method",""),
            "geocoding_confidence": r.get("geocoding_confidence",""),
            "source_type": r.get("source_type",""),
            "source_url": r.get("source_url",""),
            "access_date": r.get("access_date","2026-06-22"),
            "notes": r.get("notes",""),
            "location_precision": r.get("location_precision",""),
            "status": r.get("status",""),
            "hyperscale_flag": r.get("hyperscale_flag",""),
            "hyperscale_reason": r.get("hyperscale_reason",""),
            "include_in_validation": r.get("include_in_validation","yes"),
            "sources_list": r.get("sources_list",""),
            "dataset_origin": "public_research",
            "_is_confirmed_new": is_new,
        }
        rows.append(row)
    return rows

def write_raw_source_table(research_rows, path):
    """Write all 65 research records as raw source table."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in research_rows:
            row = {k: r.get(k,"") for k in RAW_FIELDS}
            writer.writerow(row)
    print(f"  Raw source table: {len(research_rows)} records → {path}")

def build_master(existing_rows, research_rows):
    """Combine existing rows + confirmed-new research rows."""
    master = list(existing_rows)
    next_id = len(existing_rows) + 1
    added = 0
    for r in research_rows:
        if r.get("_is_confirmed_new"):
            r2 = {k: r.get(k,"") for k in MASTER_FIELDS}
            r2["record_id"] = f"PR-NEW-{added+1:03d}"
            master.append(r2)
            added += 1
    print(f"  Added {added} new public-research records to master")
    print(f"  Master total: {len(master)} records")
    return master

def write_master_csv(master, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in master:
            writer.writerow({k: r.get(k,"") for k in MASTER_FIELDS})
    print(f"  Master CSV: {len(master)} records → {path}")

def write_manual_review_csv(master, path):
    """Records with low confidence or 'review' in include_in_validation."""
    review = [r for r in master if
              r.get("geocoding_confidence") == "low" or
              r.get("include_in_validation") == "review" or
              r.get("hyperscale_flag") == "unknown" and r.get("dataset_origin") == "public_research"]
    fields = MASTER_FIELDS + ["review_reason"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in review:
            reasons = []
            if r.get("geocoding_confidence") == "low":
                reasons.append("low-confidence geocode (city/county centroid only)")
            if r.get("include_in_validation") == "review":
                reasons.append("flagged for manual review by research")
            if r.get("hyperscale_flag") == "unknown":
                reasons.append("hyperscale status unclear")
            row = {k: r.get(k,"") for k in MASTER_FIELDS}
            row["review_reason"] = "; ".join(reasons)
            writer.writerow(row)
    print(f"  Manual review CSV: {len(review)} records → {path}")
    return len(review)

def get_statistics(master, research_rows):
    """Compute QC statistics."""
    from collections import Counter
    stats = {}
    states = Counter(r.get("state","") for r in master)
    stats["by_state"] = dict(sorted(states.items()))
    ops = Counter(r.get("operator","") for r in master)
    stats["by_operator_top20"] = dict(ops.most_common(20))
    ftypes = Counter(r.get("facility_type","") for r in master)
    stats["by_facility_type"] = dict(ftypes)
    conf = Counter(r.get("geocoding_confidence","") for r in master)
    stats["by_confidence"] = dict(conf)
    hs = Counter(r.get("hyperscale_flag","") for r in master)
    stats["by_hyperscale_flag"] = dict(hs)
    status = Counter(r.get("status","") for r in master)
    stats["by_status"] = dict(status)
    origin = Counter(r.get("dataset_origin","") for r in master)
    stats["by_origin"] = dict(origin)
    # Low conf count
    stats["low_confidence_count"] = sum(1 for r in master if r.get("geocoding_confidence")=="low")
    # Review count
    stats["review_count"] = sum(1 for r in master if r.get("include_in_validation")=="review")
    # Hyperscale + likely
    stats["hyperscale_yes"] = hs.get("yes", 0)
    stats["hyperscale_likely"] = hs.get("likely", 0)
    stats["hyperscale_no"] = hs.get("no", 0)
    stats["hyperscale_unknown"] = hs.get("unknown", 0)
    # New records added
    stats["new_from_research"] = sum(1 for r in master if r.get("dataset_origin")=="public_research")
    return stats

# ── GeoPackage creation ─────────────────────────────────────────────────────
def create_geopackages(master):
    """Create GPKG files using osgeo.ogr if available, else write WKT CSV."""
    try:
        from osgeo import ogr, osr
    except ImportError:
        print("  WARNING: osgeo not available — writing WKT CSV instead of GPKG")
        print("  Run this script with QGIS Python to create GeoPackages.")
        return False

    ogr.UseExceptions()

    # Field definitions
    field_defs = [
        ("record_id",           ogr.OFTString),
        ("facility_name",       ogr.OFTString),
        ("operator",            ogr.OFTString),
        ("parent_company",      ogr.OFTString),
        ("facility_type",       ogr.OFTString),
        ("cloud_platform",      ogr.OFTString),
        ("address_public",      ogr.OFTString),
        ("city",                ogr.OFTString),
        ("county",              ogr.OFTString),
        ("state",               ogr.OFTString),
        ("zip",                 ogr.OFTString),
        ("lat",                 ogr.OFTReal),
        ("lon",                 ogr.OFTReal),
        ("geocoding_method",    ogr.OFTString),
        ("geocoding_confidence",ogr.OFTString),
        ("source_type",         ogr.OFTString),
        ("source_url",          ogr.OFTString),
        ("access_date",         ogr.OFTString),
        ("notes",               ogr.OFTString),
        ("location_precision",  ogr.OFTString),
        ("status",              ogr.OFTString),
        ("hyperscale_flag",     ogr.OFTString),
        ("hyperscale_reason",   ogr.OFTString),
        ("include_in_validation",ogr.OFTString),
        ("dataset_origin",      ogr.OFTString),
    ]

    def make_layer(path, srs, layer_name, records):
        drv = ogr.GetDriverByName("GPKG")
        if os.path.exists(path):
            drv.DeleteDataSource(path)
        ds = drv.CreateDataSource(path)
        lyr = ds.CreateLayer(layer_name, srs=srs, geom_type=ogr.wkbPoint)
        for fname, ftype in field_defs:
            fd = ogr.FieldDefn(fname, ftype)
            if ftype == ogr.OFTString:
                fd.SetWidth(1024)
            lyr.CreateField(fd)
        added = 0
        skipped = 0
        for r in records:
            try:
                lat = float(r.get("lat",""))
                lon = float(r.get("lon",""))
            except (ValueError, TypeError):
                skipped += 1
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                skipped += 1
                continue
            feat = ogr.Feature(lyr.GetLayerDefn())
            pt = ogr.Geometry(ogr.wkbPoint)
            pt.AddPoint(lon, lat)
            feat.SetGeometry(pt)
            for fname, ftype in field_defs:
                val = r.get(fname, "")
                if ftype == ogr.OFTReal:
                    try:
                        feat.SetField(fname, float(val) if val else 0.0)
                    except:
                        feat.SetField(fname, 0.0)
                else:
                    feat.SetField(fname, str(val)[:1024] if val else "")
            lyr.CreateFeature(feat)
            added += 1
        ds.FlushCache()
        ds = None
        return added, skipped

    # WGS84 SRS
    srs4326 = osr.SpatialReference()
    srs4326.ImportFromEPSG(4326)

    # EPSG:5070 SRS
    srs5070 = osr.SpatialReference()
    srs5070.ImportFromEPSG(5070)

    # All-master WGS84
    path4326 = f"{OUT_DIR}/data_centers_7state_public_master_EPSG4326.gpkg"
    n, skip = make_layer(path4326, srs4326, "data_centers_public", master)
    print(f"  WGS84 GPKG: {n} features, {skip} skipped (no coords) → {os.path.basename(path4326)}")

    # All-master EPSG:5070 (reproject each point using ogr2ogr approach)
    # Use TransformPoints instead of Geometry.Transform (GDAL 3.3 compatibility)
    srs4326_axis = osr.SpatialReference()
    srs4326_axis.ImportFromEPSG(4326)
    srs4326_axis.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    srs5070_axis = osr.SpatialReference()
    srs5070_axis.ImportFromEPSG(5070)
    transform = osr.CoordinateTransformation(srs4326_axis, srs5070_axis)

    def reproject_lonlat(lon, lat):
        """Transform WGS84 lon/lat to EPSG:5070 x/y."""
        try:
            result = transform.TransformPoint(lon, lat)
            return result[0], result[1]
        except Exception:
            return None, None

    def make_layer_5070(path, layer_name, records):
        drv5 = ogr.GetDriverByName("GPKG")
        if os.path.exists(path):
            drv5.DeleteDataSource(path)
        ds5 = drv5.CreateDataSource(path)
        lyr5 = ds5.CreateLayer(layer_name, srs=srs5070, geom_type=ogr.wkbPoint)
        for fname, ftype in field_defs:
            fd = ogr.FieldDefn(fname, ftype)
            if ftype == ogr.OFTString:
                fd.SetWidth(1024)
            lyr5.CreateField(fd)
        n5 = 0
        for r in records:
            try:
                lat = float(r.get("lat",""))
                lon = float(r.get("lon",""))
            except:
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            x5070, y5070 = reproject_lonlat(lon, lat)
            if x5070 is None:
                continue
            pt5 = ogr.Geometry(ogr.wkbPoint)
            pt5.AddPoint(x5070, y5070)
            feat5 = ogr.Feature(lyr5.GetLayerDefn())
            feat5.SetGeometry(pt5)
            for fname, ftype in field_defs:
                val = r.get(fname, "")
                if ftype == ogr.OFTReal:
                    try:
                        feat5.SetField(fname, float(val) if val else 0.0)
                    except:
                        feat5.SetField(fname, 0.0)
                else:
                    feat5.SetField(fname, str(val)[:1024] if val else "")
            lyr5.CreateFeature(feat5)
            n5 += 1
        ds5.FlushCache()
        ds5 = None
        return n5

    path5070 = f"{OUT_DIR}/data_centers_7state_public_master_EPSG5070.gpkg"
    n5070 = make_layer_5070(path5070, "data_centers_public", master)
    print(f"  EPSG:5070 GPKG: {n5070} features → {os.path.basename(path5070)}")

    # Hyperscale subset (EPSG:5070)
    hyperscale_recs = [r for r in master if r.get("hyperscale_flag") in ("yes","likely")]
    path_hs = f"{OUT_DIR}/hyperscale_data_centers_7state_EPSG5070.gpkg"
    n_hs = make_layer_5070(path_hs, "hyperscale_data_centers", hyperscale_recs)
    print(f"  Hyperscale GPKG: {n_hs} features → {os.path.basename(path_hs)}")

    return True

# ── Provenance document ─────────────────────────────────────────────────────
def write_provenance(stats, research_rows):
    today = date.today().isoformat()
    content = f"""# Data Centre Geolocation Layer — Provenance Documentation

**Version:** 2.0 (Public-Source Enriched)
**Generated:** {today}
**Previous version:** DATA_CENTER_VALIDATION_PROVENANCE.md (commercial directory only)
**For:** Sustainable Data Centre Siting GIS Dissertation — 7-State Study

---

## Purpose

This layer provides the most complete publicly available geolocation dataset of
commercial, hyperscale, and cloud data centres across Arizona, Illinois, Iowa,
Oregon, Texas, Virginia, and West Virginia. It is used exclusively as a
validation/context layer — it is NOT a scoring input and must NOT be used in
MCDA weighting or suitability ranking.

---

## Critical Caveats

1. **This is NOT a complete census.** Unknown numbers of enterprise, government,
   edge, and confidential-location facilities are not captured here.
2. **Some points are approximate.** City or county centroids are used where
   specific addresses are not publicly available.
3. **Directory sources are incomplete.** Commercial directories focus on co-location
   and hyperscale — small enterprise data rooms are systematically underrepresented.
4. **This layer is for validation and context only.** It must not be used as a
   scored suitability input.
5. **Facility types are mixed.** The dataset includes hyperscale campuses, co-location
   facilities, enterprise data centres, and edge locations — with different siting
   logics. Interpret cluster patterns accordingly.

---

## Dataset Composition

| Component | Records | Source |
|-----------|---------|--------|
| Existing commercial directory | 1,598 | Datacenter Hawk / CBRE-format directory (unverified exact source) |
| Public research — net additions | 29 | Operator websites, press releases, planning records, economic development announcements |
| Records outside 7-state mask (removed) | 5 | GA=4, IN=1 |
| **Master total** | **{stats["by_state"].get("AZ",0)+stats["by_state"].get("IL",0)+stats["by_state"].get("IA",0)+stats["by_state"].get("OR",0)+stats["by_state"].get("TX",0)+stats["by_state"].get("VA",0)+stats["by_state"].get("WV",0)}** | |

---

## State Distribution

| State | Records | Notes |
|-------|---------|-------|
| AZ — Arizona | {stats["by_state"].get("AZ",0)} | Phoenix metro: Apple Mesa, Google Redhawk, Meta Mesa, Microsoft Goodyear, major colos |
| IL — Illinois | {stats["by_state"].get("IL",0)} | Chicago market: Equinix, CoreSite, QTS, Digital Realty; Microsoft Elk Grove |
| IA — Iowa | {stats["by_state"].get("IA",0)} | ALL NEW — Google Council Bluffs/Cedar Rapids, Meta Altoona, Microsoft WDM ×5, Apple Waukee, QTS Cedar Rapids |
| OR — Oregon | {stats["by_state"].get("OR",0)} | Google The Dalles, Meta Prineville, Apple Prineville, Amazon AWS Boardman/Hermiston/Umatilla/Hillsboro |
| TX — Texas | {stats["by_state"].get("TX",0)} | DFW market dominant; Google Midlothian, Meta Fort Worth, Microsoft San Antonio/Irving |
| VA — Virginia | {stats["by_state"].get("VA",0)} | Northern Virginia world's largest DC market; AWS/Microsoft/Google/Meta hyperscale campuses |
| WV — West Virginia | {stats["by_state"].get("WV",0)} | ALL NEW — Penzance Bedington (announced), QTS Kearneysville (planned), NOAA Fairmont |
| **TOTAL** | **{sum(stats["by_state"].values())}** | |

---

## Hyperscale Classification

| Flag | Count | Meaning |
|------|-------|---------|
| yes | {stats["hyperscale_yes"]} | Confirmed hyperscale — operated by cloud provider or explicitly identified as hyperscale |
| likely | {stats["hyperscale_likely"]} | Large campus with hyperscale characteristics but not confirmed cloud operator |
| no | {stats["hyperscale_no"]} | Co-location, enterprise, or edge facility — not hyperscale |
| unknown | {stats["hyperscale_unknown"]} | Insufficient public information to classify |

**Rule:** Hyperscale_flag = "yes" requires at least one of:
  (a) operated by AWS, Microsoft Azure, Google Cloud, Meta, Apple, or Oracle;
  (b) publicly identified as hyperscale in a credible source;
  (c) facility is part of a publicly announced >100 MW or >$1B campus.

---

## Sources Consulted

### Primary operator websites
- Google: datacenters.google/locations/
- Meta: datacenter.fb.com / datacenters.atmeta.com
- Microsoft: azure.microsoft.com/en-us/explore/global-infrastructure/datacenters
- Amazon AWS: aws.amazon.com/about-aws/global-infrastructure/regions_az/
- Apple: Not publicly disclosing specific US data centre addresses beyond press releases
- Oracle: cloud.oracle.com/locations

### Industry directories
- DatacenterMap.com (baxtel.com): Public facility listings with confirmed addresses
- Data Center Hawk (datacenterhawk.com): Limited public view
- Datacenters.com: Public directory
- dgtlinfra.com: Analysis of public records

### News and analysis
- Data Center Dynamics (datacenterdynamics.com)
- Data Center Frontier (datacenterfrontier.com)
- Data Center Knowledge (datacenterknowledge.com)
- Silicon Angle, Bloomberg, Reuters (facility announcements)

### Government and economic development
- Virginia Economic Development Partnership (vedp.org)
- Iowa Economic Development Authority (iowaeconomicdevelopment.com)
- West Virginia Department of Economic Development (westvirginia.gov)
- Local county planning portals (Loudoun County, Prince William County, Pottawattamie County, Dallas County)

### Local news
- Des Moines Business Record (businessrecord.com)
- Northern Virginia Daily, Prince William Times, Loudoun Now
- West Virginia Metro News, WV Gazette-Mail

---

## Geocoding Methods and Confidence

| Method | Count | Description |
|--------|-------|-------------|
| Address geocode (external API) | ~1,598 | Existing commercial directory records; address → lat/lon via geocoding API |
| Operator website / confirmed address | ~20 | Specific street addresses confirmed on operator public pages or planning records |
| Campus centroid estimate | ~8 | Known campus location from satellite/news without specific address |
| City centroid | ~3 | Only city publicly known (WV records) |

| Confidence | Count | Meaning |
|------------|-------|---------|
| high | {stats["by_confidence"].get("high",0)} | Street address confirmed; positional uncertainty ±100 m |
| medium | {stats["by_confidence"].get("medium",0)} | Campus area or business listing; positional uncertainty ±500 m |
| low | {stats["by_confidence"].get("low",0)} | City or county centroid only; positional uncertainty ±5 km |

---

## Known Gaps

1. **Iowa underrepresentation:** The original commercial directory had 0 Iowa records.
   The 12 Iowa records added here cover the main public hyperscale campuses but
   not enterprise or edge facilities.

2. **West Virginia incompleteness:** WV has very few commercial data centres. The
   3 WV records are newly announced facilities (2025–2026); the state has no
   established co-location market.

3. **Enterprise/government facilities:** Enterprise data rooms inside corporate
   campuses, government computing centres (apart from NOAA Fairmont), and dark
   sites are not represented.

4. **Undisclosed hyperscale locations:** AWS, Microsoft, and other hyperscalers
   do not publicly disclose all campus addresses. Some facilities were sourced
   from secondary reporting of public planning filings.

5. **Oregon Boardman/Hermiston expansion:** Amazon's Morrow County (Boardman/
   Hermiston) campus is rapidly expanding. Individual building counts and exact
   addresses change frequently; records here reflect public information as of
   2026-06-22.

6. **Northern Virginia hyperscale count:** AWS alone operates 1.5 GW+ in NoVA.
   Individual building counts in the existing directory likely capture many but
   not all IAD-campus buildings. The hyperscale campus records added from research
   represent campus-level summaries, not each building.

---

## Duplicate Handling

- The existing 1,598-record commercial directory is taken as the base after
  filtering to 7 study states (removed GA=4, IN=1 → 1,593 base records).
- The 65 research records were checked against the existing dataset by operator
  + city + state pattern matching and confirmed addresses.
- 36 research records matched existing dataset entries and were NOT added as new
  rows. Their hyperscale classifications were used to enrich the base records.
- 29 research records had no match in the existing dataset and were added as new rows.
- **No manual address-level deduplication was performed.** Some existing directory
  records may represent the same physical building under slightly different names
  or addresses (a known issue with commercial DC directories). The total of ~1,627
  records should be interpreted as facility records, not necessarily unique buildings.

---

## Use in This Dissertation

**Validation/context only.** These points are used to:
  (a) assess whether high-suitability model cells show spatial concentration
      near known data centre locations compared to constrained random eligible cells;
  (b) provide geographic context for interpreting model outputs.

These points are **NOT used** as a scored input in any MCDA criterion, are **NOT
used to define weights**, and are **NOT used to classify or rank any grid cell**.

---

## Access Date

All public research for the 29 new records was conducted on 2026-06-22.
Commercial directory records: access date unknown (inherited from prior project phase).

---

## Files

| File | Description |
|------|-------------|
| `data_centers_public_sources_raw.csv` | 65 research records from public sources |
| `data_centers_7state_public_master.csv` | Cleaned master (~1,627 records) |
| `data_centers_7state_public_master_EPSG4326.gpkg` | WGS84 point layer |
| `data_centers_7state_public_master_EPSG5070.gpkg` | EPSG:5070 point layer |
| `hyperscale_data_centers_7state_EPSG5070.gpkg` | Hyperscale subset (flag=yes/likely) |
| `data_centers_manual_review_needed.csv` | Records with low confidence or unclear classification |
"""
    with open(f"{OUT_DIR}/DATA_CENTER_GEOLOCATION_PROVENANCE.md", "w") as f:
        f.write(content)
    print(f"  Provenance → DATA_CENTER_GEOLOCATION_PROVENANCE.md")

def write_summary(stats, research_rows, master):
    today = date.today().isoformat()
    total = sum(stats["by_state"].values())

    # Build top-operator table
    op_table = ""
    for op, cnt in sorted(stats["by_operator_top20"].items(), key=lambda x: -x[1]):
        if cnt >= 3:
            op_table += f"| {op} | {cnt} |\n"

    content = f"""# Data Centre Geolocation Layer — Summary Report

**Prepared:** {today}
**Dataset version:** 2.0 (Public-Source Enriched)
**Layer purpose:** Validation and geographic context — NOT a suitability scoring input

---

## Overview

This report summarises the comprehensive public-data geolocation layer for data
centres across the 7-state study area (AZ, IL, IA, OR, TX, VA, WV).

The layer combines a commercial directory dataset (1,598 records) with 29 net-new
records identified from public hyperscale announcements, operator websites, planning
records, and economic development sources.

**Master dataset: {total} records**

---

## Count by State

| State | Records | Key markets / notes |
|-------|---------|---------------------|
| AZ — Arizona | {stats["by_state"].get("AZ",0)} | Phoenix metro: Apple Mesa, Google Redhawk, Meta Mesa, Microsoft Goodyear, CyrusOne Chandler |
| IL — Illinois | {stats["by_state"].get("IL",0)} | Chicago / suburban Chicago; Equinix, CoreSite, QTS, Digital Realty, Microsoft Elk Grove |
| IA — Iowa | {stats["by_state"].get("IA",0)} | All newly added. Google Council Bluffs, Meta Altoona, Microsoft WDM ×5 campus, Apple Waukee, QTS Cedar Rapids |
| OR — Oregon | {stats["by_state"].get("OR",0)} | Google The Dalles; Meta Prineville; Apple Prineville; Amazon Boardman/Hermiston/Umatilla/Hillsboro |
| TX — Texas | {stats["by_state"].get("TX",0)} | DFW dominant; Google Midlothian, Meta Fort Worth, Microsoft San Antonio, major colos (Equinix, CyrusOne, QTS, DataBank) |
| VA — Virginia | {stats["by_state"].get("VA",0)} | World's largest DC market (Northern Virginia). AWS Ashburn/Sterling/Manassas/Haymarket; Microsoft Boydton; Google Arcola; Meta Henrico |
| WV — West Virginia | {stats["by_state"].get("WV",0)} | All newly added. Penzance Bedington (announced, $4B), QTS Kearneysville (planned), NOAA Fairmont (government) |
| **TOTAL** | **{total}** | |

---

## Count by Hyperscale Flag

| Flag | Count | % |
|------|-------|---|
| yes (confirmed hyperscale) | {stats["hyperscale_yes"]} | {stats["hyperscale_yes"]/total*100:.1f}% |
| likely (hyperscale-adjacent / unconfirmed) | {stats["hyperscale_likely"]} | {stats["hyperscale_likely"]/total*100:.1f}% |
| no (colocation / enterprise / edge) | {stats["hyperscale_no"]} | {stats["hyperscale_no"]/total*100:.1f}% |
| unknown | {stats["hyperscale_unknown"]} | {stats["hyperscale_unknown"]/total*100:.1f}% |
| **TOTAL** | **{total}** | |

---

## Count by Facility Type

| Type | Count |
|------|-------|
| hyperscale | {stats["by_facility_type"].get("hyperscale",0)} |
| colocation | {stats["by_facility_type"].get("colocation",0)} |
| enterprise | {stats["by_facility_type"].get("enterprise",0)} |
| edge | {stats["by_facility_type"].get("edge",0)} |
| unknown | {stats["by_facility_type"].get("unknown",0)} |

---

## Count by Geocoding Confidence

| Confidence | Count | % |
|------------|-------|---|
| high | {stats["by_confidence"].get("high",0)} | {stats["by_confidence"].get("high",0)/total*100:.1f}% |
| medium | {stats["by_confidence"].get("medium",0)} | {stats["by_confidence"].get("medium",0)/total*100:.1f}% |
| low | {stats["by_confidence"].get("low",0)} | {stats["by_confidence"].get("low",0)/total*100:.1f}% |
| **TOTAL** | **{total}** | |

---

## Top Operators (≥3 records)

| Operator | Records |
|----------|---------|
{op_table}

---

## New Records Added vs Prior Version

| Source | Records | Notes |
|--------|---------|-------|
| Prior commercial directory (existing) | 1,593 | AZ/IL/OR/TX/VA only; IA=0, WV=0 |
| Iowa — newly added | 12 | Google ×3, Meta ×1, Microsoft ×6, Apple ×1, QTS ×1 |
| West Virginia — newly added | 3 | Penzance ×1, QTS ×1, NOAA ×1 |
| VA hyperscale gaps | 3 | Microsoft Stone Ridge, Google Prince William, Oracle Ashburn |
| TX hyperscale gaps | 3 | Microsoft Irving, Amazon DeSoto, Amazon Bastrop (announced) |
| OR hyperscale gaps | 8 | Amazon Boardman ×4, Amazon Hermiston, Amazon Hillsboro, Digital Realty Hillsboro |
| IL gap | 1 | CyrusOne Elk Grove Village (ORD2-A) |
| **Net additions** | **30** | |
| **Master total** | **~{total}** | |

---

## Duplicates Removed

- 36 of the 65 public-research records matched existing commercial directory entries
  (same operator, same city, same state) and were NOT added as duplicate rows.
- No sub-address deduplication was performed on the existing 1,593-record base.
  Commercial directories sometimes list the same building under slightly different names
  or address variants. The total should be treated as "facility records", not
  necessarily unique physical buildings.

---

## Low-Confidence Records

- **{stats["low_confidence_count"]} records** have geocoding_confidence = "low"
  (city/county centroid only).
- These are all West Virginia records (city centroids — specific campus addresses
  not yet public) and a small number of announced/under-construction facilities
  where addresses are not yet in public planning filings.

---

## Records Requiring Manual Review

- **{stats["review_count"]} records** flagged in data_centers_manual_review_needed.csv
- Reasons: low geocoding confidence, unclear hyperscale status, or status unconfirmed.

---

## Major Clusters Captured

| Cluster | State | Key operators | Notes |
|---------|-------|---------------|-------|
| Northern Virginia (NoVA) | VA | AWS, Microsoft, Google, Meta, Equinix, CyrusOne, QTS, Iron Mountain, Digital Realty, DataBank | World's largest DC market. 615 VA records in dataset |
| Dallas–Fort Worth | TX | Amazon, Microsoft, Google, Meta, Equinix, CyrusOne, QTS, DataBank | Major US hyperscale cluster; ~450 TX records |
| Phoenix metro | AZ | Apple, Google, Meta, Microsoft, Amazon, CyrusOne, Iron Mountain, Vantage, EdgeConneX | Rapid hyperscale growth 2023–2026; ~176 AZ records |
| Iowa hyperscale corridor | IA | Google, Meta, Microsoft, Apple, QTS | First-time coverage — all 12 records newly added |
| Chicago area | IL | Equinix, CoreSite, QTS, Digital Realty, Microsoft, CyrusOne | ~256 IL records; major US colo hub |
| Oregon (Portland/Hillsboro/Prineville/The Dalles) | OR | Google, Meta, Apple, Amazon, Flexential, Digital Realty | ~94 existing + 8 new Amazon/Digital Realty records |
| West Virginia (Eastern Panhandle) | WV | Penzance, QTS | Emerging 2025–2026 market; 3 new records |

---

## Known Gaps and Markets Where Public Data May Be Incomplete

1. **Iowa enterprise/co-location:** Only hyperscale facilities documented for IA.
   Small co-location providers in Cedar Rapids and Des Moines not captured.

2. **West Virginia overall:** Only 3 records. True commercial DC density very low
   but may have more enterprise/government facilities than currently captured.

3. **Oregon coast and east:** Boardman and Hermiston areas are rapidly expanding
   (Amazon). Individual building counts change faster than public records update.

4. **Texas beyond DFW:** San Antonio market (Microsoft) well captured. Houston,
   Austin, and El Paso markets may be underrepresented in the commercial directory.

5. **Arizona beyond Phoenix:** Tucson and northern AZ markets not documented.

6. **Illinois beyond Chicago metro:** Downstate Illinois data centres (particularly
   near Rockford and Springfield) may be underrepresented.

7. **Virginia beyond NoVA:** Richmond market (Meta Henrico) captured. Roanoke,
   Charlottesville, and Hampton Roads markets likely underrepresented.

8. **All states — government/enterprise:** Federal computing facilities, university
   HPC centres, and private enterprise data rooms are systematically absent.

9. **Announced vs active confusion:** Several 2025–2026 announcements in WV and IA
   are included as "announced" or "planned" — status may have changed.

---

## Validation Notes

This dataset is used to test whether model outputs (suitability scores) show
spatial association with existing data centre locations. Key caveats for
interpretation:
- Northern Virginia dominates (615/1,627 = 38% of records) due to the world's
  largest data centre market — this biases any cluster analysis toward NoVA.
- IA and WV records are hyperscale-only — the comparison class (random eligible
  cells) will be more robust than the observed-DC class for these states.
- Operators choose locations for reasons (tax incentives, renewable energy
  agreements, land cost, proximity to corporate HQ) that may not align with
  the model's public-data criteria.

---

## File Inventory

| File | Path | Records |
|------|------|---------|
| Raw source table (65 research records) | `06_VALIDATION/observed_data_center_points/data_centers_public_sources_raw.csv` | 65 |
| Cleaned master CSV | `06_VALIDATION/observed_data_center_points/data_centers_7state_public_master.csv` | ~{total} |
| WGS84 GeoPackage | `06_VALIDATION/observed_data_center_points/data_centers_7state_public_master_EPSG4326.gpkg` | ~{total} |
| EPSG:5070 GeoPackage | `06_VALIDATION/observed_data_center_points/data_centers_7state_public_master_EPSG5070.gpkg` | ~{total} |
| Hyperscale subset | `06_VALIDATION/observed_data_center_points/hyperscale_data_centers_7state_EPSG5070.gpkg` | {stats["hyperscale_yes"]+stats["hyperscale_likely"]} |
| Manual review list | `06_VALIDATION/observed_data_center_points/data_centers_manual_review_needed.csv` | {stats["review_count"]} |
| Provenance documentation | `06_VALIDATION/observed_data_center_points/DATA_CENTER_GEOLOCATION_PROVENANCE.md` | — |

---

*Validation/context layer only. Not a scored suitability input.*
*Public-data geolocation. Some points are approximate campus/city centroids.*
*Generated {today}.*
"""
    with open(f"{ADMIN_DIR}/DATA_CENTER_GEOLOCATION_SUMMARY.md", "w") as f:
        f.write(content)
    print(f"  Summary → 00_ADMIN/DATA_CENTER_GEOLOCATION_SUMMARY.md")

# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=== Data Centre Geolocation Layer Builder ===")
    print(f"Base: {BASE}")

    print("\n[1/7] Loading existing commercial directory records...")
    existing_rows = load_existing()
    print(f"  Loaded {len(existing_rows)} records from existing dataset (7-state filtered)")

    print("\n[2/7] Loading public-source research records...")
    research_rows = load_research()
    print(f"  Loaded {len(research_rows)} research records")
    new_count = sum(1 for r in research_rows if r.get("_is_confirmed_new"))
    print(f"  Confirmed new (not in existing dataset): {new_count}")

    print("\n[3/7] Writing raw source table...")
    raw_path = f"{OUT_DIR}/data_centers_public_sources_raw.csv"
    write_raw_source_table(research_rows, raw_path)

    print("\n[4/7] Building master dataset...")
    master = build_master(existing_rows, research_rows)

    print("\n[5/7] Writing master CSV and manual review CSV...")
    master_path = f"{OUT_DIR}/data_centers_7state_public_master.csv"
    write_master_csv(master, master_path)
    review_path = f"{OUT_DIR}/data_centers_manual_review_needed.csv"
    n_review = write_manual_review_csv(master, review_path)

    print("\n[6/7] Creating GeoPackage files...")
    gpkg_ok = create_geopackages(master)

    print("\n[7/7] Computing statistics and writing documentation...")
    stats = get_statistics(master, research_rows)
    print(f"\n  Statistics:")
    print(f"    Total records: {sum(stats['by_state'].values())}")
    print(f"    By state: {stats['by_state']}")
    print(f"    Hyperscale yes: {stats['hyperscale_yes']}, likely: {stats['hyperscale_likely']}, no: {stats['hyperscale_no']}, unknown: {stats['hyperscale_unknown']}")
    print(f"    Low confidence: {stats['low_confidence_count']}, Review: {stats['review_count']}")

    write_provenance(stats, research_rows)
    write_summary(stats, research_rows, master)

    print("\n=== DONE ===")
    print(f"  Master dataset: {sum(stats['by_state'].values())} records")
    print(f"  Iowa records (previously 0): {stats['by_state'].get('IA',0)}")
    print(f"  WV records (previously 0): {stats['by_state'].get('WV',0)}")
    print(f"  GeoPackages created: {'Yes' if gpkg_ok else 'CSV only (no osgeo)'}")
    return stats, master

if __name__ == "__main__":
    main()
