"""Load real Nigerian health facilities (GRID3 v3.0 + v2.0, built from the Nigeria Health Facility Registry).

The data has names, types, ownership, level and coordinates but no opening hours or
service lists, so Lafiya infers *likely* services and *typical* hours from the facility
type and marks them unverified (hours_verified=False) — the UI says "call to confirm".
"""

import csv
import gzip
import hashlib
import re
from datetime import time
from pathlib import Path

from django.db import transaction

from .geo import haversine_km, nearest_facilities
from .geography import _key
from .models import LGA, Facility

DATA_FILE = Path(__file__).parent / "data" / "nigeria_health_facilities.csv.gz"
ALL_SERVICES = "immunization,antenatal,delivery,malaria,ncd,nutrition,emergency"


def classify(facility_type, level):
    t, lvl = facility_type.lower(), level.lower()
    if "teaching" in t or "tertiary" in t or "federal medical" in t:
        return "th"
    if "general hospital" in t:
        return "gh"
    if "comprehensive" in t:
        return "chc"
    if "hospital" in t or "medical cent" in t or "cottage" in t:
        return "hosp"
    if "maternity" in t:
        return "mat"
    if "health post" in t:
        return "hp"
    if "primary health" in t or "health cent" in t or "health centre" in t:
        return "phc"
    if "clinic" in t:
        return "clin"
    if lvl in ("secondary", "tertiary"):
        return "hosp"
    if lvl == "primary":
        return "phc"
    return "oth"


def likely_services(ftype, ownership):
    public = ownership.lower() != "private"
    if ftype in Facility.HOSPITAL_TYPES:
        return ALL_SERVICES if public else "antenatal,delivery,malaria,ncd,nutrition,emergency"
    if ftype == "phc":
        return "immunization,antenatal,delivery,malaria,nutrition,ncd" if public else "antenatal,delivery,malaria,ncd"
    if ftype == "hp":
        return "immunization,malaria,nutrition"
    if ftype == "mat":
        return "immunization,antenatal,delivery" if public else "antenatal,delivery"
    if ftype == "clin":
        return "immunization,malaria,nutrition,antenatal" if public else "malaria,ncd,antenatal"
    return "malaria"


# Facilities that mainly serve a closed group — not suitable for public referrals by service.
RESTRICTED = re.compile(
    r"\b(staff (clinic|health)|barrack|police|prison|correctional|nysc|camp clinic|military|army|navy|"
    r"air ?force|school clinic|college clinic|university (health|clinic|medical)|polytechnic|"
    r"house of assembly|secretariat|company clinic|refinery)\b",
    re.I,
)


def is_restricted(name):
    return bool(RESTRICTED.search(name))


def typical_hours(ftype):
    """(is_24h, open_days, opens, closes) — typical, unverified."""
    if ftype in Facility.HOSPITAL_TYPES or ftype == "mat":
        return True, "0123456", time(0), time(23, 59)
    return False, "01234", time(8), time(16)


def external_id(row):
    raw = f"{row['name']}|{float(row['latitude']):.5f}|{float(row['longitude']):.5f}"
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


class LGAResolver:
    """Match a facility's state/LGA text to one of the 774 LGAs; fall back to the nearest LGA in that state."""

    def __init__(self):
        self.by_name, self.by_state = {}, {}
        for lga in LGA.objects.select_related("state"):
            skey = _key(lga.state.name)
            self.by_name[(skey, _key(lga.name))] = lga
            self.by_state.setdefault(skey, []).append(lga)
        self.all = [l for ls in self.by_state.values() for l in ls]

    def __call__(self, state, lga, lat, lon):
        skey = _key(state)
        found = self.by_name.get((skey, _key(lga)))
        if found:
            return found
        candidates = self.by_state.get(skey) or self.all
        return min(candidates, key=lambda l: haversine_km(lat, lon, l.latitude, l.longitude))


def rows(path=DATA_FILE):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


@transaction.atomic
def load_facilities(path=DATA_FILE, replace_demo=True):
    resolve = LGAResolver()
    existing = dict(Facility.objects.exclude(external_id=None).values_list("external_id", "id"))
    new, seen = [], set()
    for row in rows(path):
        eid = external_id(row)
        if eid in existing or eid in seen:
            continue
        seen.add(eid)
        lat, lon = float(row["latitude"]), float(row["longitude"])
        ftype = classify(row["facility_type"], row["level"])
        is_24h, days, opens, closes = typical_hours(ftype)
        new.append(
            Facility(
                name=re.sub(r"\s+", " ", row["name"]).strip()[:150],
                facility_type=ftype,
                level=row["level"][:10],
                ownership=row["ownership"][:10],
                functional=row["functional"][:25],
                registry_code=row["registry_code"][:40],
                source=row["source"],
                external_id=eid,
                lga=resolve(row["state"], row["lga"], lat, lon),
                address=", ".join(x for x in (row["ward"], row["lga"], row["state"]) if x)[:200],
                latitude=lat,
                longitude=lon,
                # Restricted-access sites keep no services, so they never appear in service referrals.
                services="" if is_restricted(row["name"]) else likely_services(ftype, row["ownership"]),
                is_24h=is_24h,
                open_days=days,
                opens_at=opens,
                closes_at=closes,
                hours_verified=False,
            )
        )
    Facility.objects.bulk_create(new, batch_size=2000)
    replaced = replace_demo_facilities() if replace_demo else 0
    return {"created": len(new), "already_loaded": len(existing), "demo_replaced": replaced,
            "total": Facility.objects.count()}


def replace_demo_facilities():
    """Re-point everything that referenced synthetic demo facilities to the nearest real one, then delete them."""
    from alerts.models import Alert
    from core.models import Profile
    from immunitrack.models import Immunization
    from mamacare.models import ANCVisit
    from navigator.models import Referral

    demo = list(Facility.objects.filter(source="demo"))
    if not demo or not Facility.objects.exclude(source="demo").exists():
        return 0
    for f in demo:
        main = f.service_list[0] if f.service_list else None
        target = next(
            (r for r, _ in nearest_facilities((f.latitude, f.longitude), service=main, limit=10) if r.source != "demo"),
            None,
        ) or next((r for r, _ in nearest_facilities((f.latitude, f.longitude), limit=10) if r.source != "demo"), None)
        if target is None:
            continue
        for model, field in ((Referral, "facility"), (Profile, "facility"), (ANCVisit, "facility"),
                             (Immunization, "facility"), (Alert, "facility")):
            model.objects.filter(**{field: f}).update(**{field: target})
        f.delete()
    return len(demo)
