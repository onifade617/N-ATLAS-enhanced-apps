"""Build core/data/nigeria_health_facilities.csv.gz from GRID3 health-facility GeoPackages.

Sources (CC BY 4.0, GRID3 — built from the Nigeria Health Facility Registry, NPHCDA and field surveys):
  v3.0 (24 states, newer):   https://data.humdata.org/dataset/grid3-nga-health-facilities-v3-0
  v2.0 (all 37 states):      https://data.humdata.org/dataset/grid3-nga-health-facilities-v2-0

v3.0 is used for the states it covers; v2.0 fills the remaining states. Facilities that are
closed / not functional or have no coordinates are dropped.

Usage (stdlib only — a GeoPackage is an SQLite database):
    python scripts/build_facilities_csv.py path/to/grid3_v3.gpkg path/to/grid3_v2.gpkg
"""

import csv
import gzip
import sqlite3
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "core" / "data" / "nigeria_health_facilities.csv.gz"
FIELDS = ["source", "registry_code", "name", "facility_type", "level", "ownership", "functional",
          "state", "lga", "ward", "latitude", "longitude"]
STATE_NAMES = {"fct": "Federal Capital Territory", "fct, abuja": "Federal Capital Territory"}


def state_name(raw):
    raw = (raw or "").strip()
    return STATE_NAMES.get(raw.lower(), raw)


def clean(v):
    return (v or "").strip() if isinstance(v, str) else ("" if v is None else str(v))


def read_v3(path):
    c = sqlite3.connect(path)
    q = """select nhfr_facility_code, facility_name, facility_type, facility_level, facility_ownership, functional,
                  state_standard, lga_standard, ward_standard, latitude, longitude
           from GRID3_NGA_health_facilities_v3_0"""
    for code, name, ftype, level, own, functional, state, lga, ward, lat, lon in c.execute(q):
        yield {"source": "GRID3 v3.0", "registry_code": clean(code), "name": clean(name), "facility_type": clean(ftype),
               "level": clean(level), "ownership": clean(own), "functional": clean(functional),
               "state": state_name(state), "lga": clean(lga), "ward": clean(ward), "latitude": lat, "longitude": lon}


def read_v2(path):
    c = sqlite3.connect(path)
    q = """select nhfr_facility_code, facility_name, facility_level_option, facility_level, ownership,
                  state, lga, ward, latitude, longitude
           from NGA_health_facilities_v2_0"""
    for code, name, ftype, level, own, state, lga, ward, lat, lon in c.execute(q):
        yield {"source": "GRID3 v2.0", "registry_code": clean(code), "name": clean(name), "facility_type": clean(ftype),
               "level": clean(level), "ownership": clean(own), "functional": "",
               "state": state_name(state), "lga": clean(lga), "ward": clean(ward), "latitude": lat, "longitude": lon}


def usable(row):
    try:
        lat, lon = float(row["latitude"]), float(row["longitude"])
    except (TypeError, ValueError):
        return False
    return (row["name"] and 4.0 <= lat <= 14.0 and 2.5 <= lon <= 15.0
            and row["functional"] not in ("Closed", "Not-Functional"))


def main(v3_path, v2_path):
    v3 = [r for r in read_v3(v3_path) if usable(r)]
    v3_states = {r["state"].lower() for r in v3}
    v2 = [r for r in read_v2(v2_path) if usable(r) and r["state"].lower() not in v3_states]
    rows = sorted(v3 + v2, key=lambda r: (r["state"], r["lga"], r["name"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            r["latitude"], r["longitude"] = round(float(r["latitude"]), 6), round(float(r["longitude"]), 6)
            w.writerow(r)
    states = {r["state"] for r in rows}
    print(f"{len(rows)} facilities in {len(states)} states ({len(v3)} from v3.0, {len(v2)} from v2.0) -> {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
