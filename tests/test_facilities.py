"""Real health-facility import (GRID3 / Health Facility Registry), fast nearest search and honest hours."""

import csv
import gzip
import random
import tempfile
from datetime import time
from pathlib import Path

from django.test import TestCase

from core.facilities_data import classify, is_restricted, likely_services, load_facilities
from core.geo import haversine_km, nearest_facilities
from core.geography import load_geography
from core.models import LGA, Facility, Profile
from navigator.engine import respond
from navigator.models import Referral

COLUMNS = ["source", "registry_code", "name", "facility_type", "level", "ownership", "functional",
           "state", "lga", "ward", "latitude", "longitude"]


def write_fixture(rows):
    path = Path(tempfile.mkdtemp()) / "fac.csv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})
    return path


class FacilityImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_geography()
        cls.ibadan = LGA.objects.get(name="Ibadan North")

    def test_classify_and_likely_services(self):
        self.assertEqual(classify("Primary Health Center", "Primary"), "phc")
        self.assertEqual(classify("General Hospital", "Secondary"), "gh")
        self.assertEqual(classify("Teaching/Tertiary\xa0Hospital", "Tertiary"), "th")
        self.assertEqual(classify("Health Post", "Primary"), "hp")
        self.assertEqual(classify("", "Secondary"), "hosp")
        self.assertIn("immunization", likely_services("phc", "Public"))
        self.assertNotIn("immunization", likely_services("clin", "Private"))
        self.assertIn("emergency", likely_services("gh", "Public"))
        self.assertTrue(is_restricted("Secretariat Staff Clinic"))
        self.assertTrue(is_restricted("Nysc Camp Borno Camp Clinic"))
        self.assertTrue(is_restricted("Police Barracks Clinic"))
        self.assertFalse(is_restricted("Obasa Primary Health Centre"))

    def test_load_matches_lgas_and_replaces_demo(self):
        demo = Facility.objects.create(name="Demo PHC", source="demo", lga=self.ibadan, latitude=7.42, longitude=3.90,
                                       services="immunization,antenatal")
        mum = Profile.objects.create(full_name="Mum", lga=self.ibadan, consent_given=True)
        Referral.objects.create(profile=mum, facility=demo, reason="test")
        path = write_fixture([
            {"source": "GRID3 v3.0", "name": "Real PHC Ibadan", "facility_type": "Primary Health Center",
             "level": "Primary", "ownership": "Public", "state": "Oyo", "lga": "Ibadan North",
             "latitude": 7.421, "longitude": 3.901, "registry_code": "30/01/1/1/1/0001"},
            # Unmatched spellings: resolved to the nearest LGA in that state
            {"source": "GRID3 v3.0", "name": "AMAC Clinic", "facility_type": "Clinic", "level": "Primary",
             "ownership": "Private", "state": "Federal Capital Territory", "lga": "Municipal Area Council",
             "latitude": 9.06, "longitude": 7.49},
        ])
        result = load_facilities(path)
        self.assertEqual((result["created"], result["demo_replaced"]), (2, 1))
        real = Facility.objects.get(name="Real PHC Ibadan")
        self.assertEqual(real.lga, self.ibadan)
        self.assertFalse(real.hours_verified)
        self.assertEqual(Facility.objects.get(name="AMAC Clinic").lga.name, "Abuja Municipal")
        self.assertEqual(Referral.objects.get().facility, real)  # re-pointed, not deleted
        self.assertFalse(Facility.objects.filter(source="demo").exists())
        self.assertEqual(load_facilities(path)["created"], 0)  # idempotent

    def test_nearest_matches_brute_force(self):
        rng = random.Random(7)
        Facility.objects.bulk_create(
            Facility(name=f"F{i}", lga=self.ibadan, latitude=rng.uniform(4.5, 13.5), longitude=rng.uniform(3, 14),
                     services=rng.choice(["immunization,malaria", "malaria", "emergency"]))
            for i in range(600)
        )
        for _ in range(25):
            origin = (rng.uniform(4.5, 13.5), rng.uniform(3, 14))
            got = [f.name for f, _ in nearest_facilities(origin, service="immunization", limit=4)]
            brute = sorted(
                (f for f in Facility.objects.all() if f.offers("immunization")),
                key=lambda f: haversine_km(*origin, f.latitude, f.longitude),
            )[:4]
            self.assertEqual(got, [f.name for f in brute])

    def test_unverified_hours_are_not_claimed_as_fact(self):
        Facility.objects.create(name="Real PHC", lga=self.ibadan, latitude=7.42, longitude=3.90, source="GRID3 v3.0",
                                services="immunization,malaria", hours_verified=False, open_days="0123456",
                                opens_at=time(0), closes_at=time(23, 59))
        mum = Profile.objects.create(full_name="Ade Mum", lga=self.ibadan, consent_given=True)
        r = respond(mum, "where is the nearest clinic?", language="en")
        self.assertIn("usually open at this time (hours not confirmed)", r["reply"])
        self.assertNotIn("It is open now", r["reply"])
        self.assertFalse(r["facilities"][0]["hours_verified"])

    def test_facilities_api_filters_and_pages(self):
        for i in range(3):
            Facility.objects.create(name=f"P{i}", lga=self.ibadan, latitude=7.4, longitude=3.9, services="malaria")
        data = self.client.get(f"/api/v1/facilities/?lga={self.ibadan.pk}&limit=2").json()
        self.assertEqual((data["count"], len(data["results"])), (3, 2))
        self.assertEqual(self.client.get("/api/v1/facilities/?limit=x").status_code, 400)
