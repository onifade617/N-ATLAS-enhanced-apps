import json
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from alerts.engine import run_loop
from alerts.models import Alert
from climateguard.models import RiskAssessment, WeatherDay
from climateguard.risk import assess_lga, flood_risk, heat_risk, malaria_risk
from core.management.commands.seed_lafiya import DANGER_SIGNS, VACCINES
from core.models import LGA, Child, Facility, Profile, State
from immunitrack.models import Immunization, Vaccine
from immunitrack.services import coverage_for_children, next_due
from mamacare.models import DangerSign, Pregnancy
from navigator.engine import normalize, respond
from navigator.models import Referral

TODAY = date.today()


class Day:
    def __init__(self, tmax=31, tmin=23, app=33, rain=0, hum=80, d=TODAY):
        self.temp_max, self.temp_min, self.apparent_temp_max = tmax, tmin, app
        self.precipitation_mm, self.humidity_mean, self.date = rain, hum, d


@override_settings(CLIMATE_LIVE_WEATHER=False, NATLAS={"API_URL": "", "API_KEY": "", "MODEL": "x", "TIMEOUT": 1})
class LafiyaTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        state = State.objects.create(name="Oyo", code="OY")
        cls.lga = LGA.objects.create(state=state, name="Ibadan North", latitude=7.4167, longitude=3.9)
        cls.phc = Facility.objects.create(
            name="Test PHC", lga=cls.lga, latitude=7.42, longitude=3.9, services="immunization,antenatal,malaria,ncd",
            open_days="0123456", opens_at=time(0), closes_at=time(23, 59),
        )
        cls.gh = Facility.objects.create(
            name="Test General Hospital", facility_type="gh", lga=cls.lga, latitude=7.45, longitude=3.95,
            services="immunization,antenatal,malaria,ncd,emergency", is_24h=True, open_days="0123456",
        )
        for i, (code, name, protects, days, label) in enumerate(VACCINES):
            Vaccine.objects.create(code=code, name=name, protects_against=protects, age_days=days, age_label=label, sort_order=i)
        DangerSign.objects.bulk_create(DangerSign(category=c, sign=s, keywords=k) for c, s, k in DANGER_SIGNS)

        def user(username, role=Profile.ROLE_FAMILY, **kw):
            u = User.objects.create_user(username, password="pw123456", is_staff=role == Profile.ROLE_GOV)
            return Profile.objects.create(user=u, full_name=f"{username.title()} Test", lga=cls.lga, role=role,
                                          consent_given=True, **kw)

        cls.funke = user("funke", language="yo")
        cls.tobi = Child.objects.create(caregiver=cls.funke, name="Tobi", sex="M", date_of_birth=TODAY - timedelta(days=41))
        for code in ("BCG", "OPV0", "HEPB0"):
            Immunization.objects.create(child=cls.tobi, vaccine=Vaccine.objects.get(code=code), given_date=cls.tobi.date_of_birth)
        cls.mama = user("mama", has_hypertension=True)
        Pregnancy.objects.create(profile=cls.mama, lmp_date=TODAY - timedelta(weeks=20))
        cls.worker = user("worker", role=Profile.ROLE_WORKER, facility=cls.phc)
        cls.gov = user("gov", role=Profile.ROLE_GOV)

    def login(self, username):
        self.client.login(username=username, password="pw123456")


class ScheduleTests(LafiyaTestCase):
    def test_six_week_vaccines_are_next(self):
        nd = next_due(self.tobi)
        self.assertEqual(nd["due_date"], self.tobi.date_of_birth + timedelta(days=42))
        self.assertIn("PENTA1", [v.code for v in nd["vaccines"]])
        self.assertEqual(nd["status"], "due_soon")

    def test_anc_schedule_has_eight_contacts(self):
        preg = self.mama.active_pregnancy
        self.assertEqual(preg.visits.count(), 8)
        self.assertEqual(preg.edd, preg.lmp_date + timedelta(days=280))
        # Contact 1 (week 12) was missed before enrolment; next is contact 2 (week 20).
        self.assertEqual(preg.next_visit().contact_number, 2)

    def test_zero_dose_and_coverage(self):
        older = Child.objects.create(caregiver=self.mama, name="Old", sex="F", date_of_birth=TODAY - timedelta(days=200))
        stats = coverage_for_children([self.tobi, older])
        self.assertEqual(stats["zero_dose"], 1)
        self.assertEqual(stats["penta1_coverage"], 0)


class RiskTests(LafiyaTestCase):
    def test_malaria_thresholds(self):
        score, level, why, _ = malaria_risk([Day(rain=7, hum=80) for _ in range(14)])
        self.assertEqual((score, level), (100, "very_high"))
        self.assertIn("98 mm", why)
        score, level, _, _ = malaria_risk([Day(tmax=40, tmin=30, rain=0, hum=20) for _ in range(14)])
        self.assertEqual(level, "low")

    def test_heat_and_flood_thresholds(self):
        self.assertEqual(heat_risk([Day(app=41)])[1], "very_high")
        self.assertEqual(heat_risk([Day(app=38)] * 3)[1], "very_high")  # 3 hot days bumps high -> very high
        self.assertEqual(heat_risk([Day(app=30)])[1], "low")
        self.assertEqual(flood_risk([Day(rain=40)] * 3)[1], "very_high")
        self.assertEqual(flood_risk([Day(rain=0), Day(rain=55), Day(rain=0)])[1], "high")

    def test_assess_and_trend(self):
        for i in range(-21, 7):
            d = TODAY + timedelta(days=i)
            WeatherDay.objects.create(lga=self.lga, date=d, temp_max=31, temp_min=23, apparent_temp_max=33,
                                      precipitation_mm=8 if i >= -14 else 0, humidity_mean=80, is_forecast=i > 0)
        assess_lga(self.lga, TODAY - timedelta(days=7))
        assess_lga(self.lga, TODAY)
        malaria = RiskAssessment.objects.get(lga=self.lga, date=TODAY, hazard="malaria")
        self.assertEqual(malaria.trend, "rising")
        self.assertTrue(malaria.explanation)


class NavigatorTests(LafiyaTestCase):
    def test_pitch_scenario_in_yoruba(self):
        r = respond(self.funke, "Abẹ́rẹ́ àjẹsára wo ni ọmọ ọlọ́sẹ̀ mẹ́fà mi nílò báyìí?")
        self.assertEqual(r["intent"], "vaccine")
        self.assertIn("Pentavalent 1", r["reply"])
        self.assertIn("Abẹ́rẹ́ àjẹsára", r["reply"])  # answered in Yoruba
        self.assertIsNotNone(r["reminder"])  # books the reminder
        self.assertTrue(Alert.objects.filter(profile=self.funke, kind="reminder").exists())
        self.assertTrue(r["facilities"][0]["open_now"])  # points to an open clinic

    def test_emergency_always_refers(self):
        r = respond(self.mama, "I am pregnant and bleeding", language="en")
        self.assertTrue(r["emergency"])
        self.assertIn("112", r["reply"])
        self.assertEqual(Referral.objects.get(pk=r["referral_id"]).urgency, "emergency")

    def test_symptom_referral_and_topics(self):
        r = respond(self.mama, "my child has fever", language="en")
        self.assertEqual(r["intent"], "fever")
        self.assertIsNotNone(r["referral_id"])
        r = respond(self.mama, "how do I control my blood pressure", language="en")
        self.assertEqual(r["intent"], "hypertension")
        self.assertIn("salt", r["reply"])

    def test_keyword_boundaries(self):
        self.assertEqual(normalize("Ọ̀sẹ̀"), "ose")
        self.assertNotEqual(respond(self.mama, "imeela", language="ig")["intent"], "pregnancy")


class LoopTests(LafiyaTestCase):
    def test_intelligence_loop_creates_personal_alerts(self):
        summary = run_loop(TODAY, refresh_weather=True, live=False)
        self.assertEqual(summary["weather_sources"], {"simulated": 1})
        vax = Alert.objects.get(profile=self.funke, kind="vaccine")
        self.assertIn("Tobi", vax.message)
        self.assertEqual(vax.language, "yo")
        self.assertTrue(vax.reason)
        # Idempotent: running again does not duplicate alerts.
        before = Alert.objects.count()
        run_loop(TODAY, refresh_weather=False)
        self.assertEqual(Alert.objects.count(), before)


class ViewTests(LafiyaTestCase):
    def setUp(self):
        run_loop(TODAY, refresh_weather=True, live=False)

    def test_public_pages(self):
        for url in ("/", "/login/", "/signup/", "/climate/", "/facilities/", "/api/v1/", "/api/v1/lgas/", "/api/v1/facilities/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_family_pages(self):
        self.login("funke")
        for url in ("/home/", "/mamacare/", "/immunitrack/", f"/immunitrack/child/{self.tobi.pk}/", "/alerts/",
                    "/navigator/", "/profile/", "/profile/export/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get("/gov/").status_code, 302)  # role protected

    def test_navigator_api(self):
        self.login("funke")
        res = self.client.post("/navigator/api/ask/", json.dumps({"text": "which vaccine next?", "language": "en"}),
                               content_type="application/json")
        data = res.json()
        self.assertEqual(data["intent"], "vaccine")
        res = self.client.post("/navigator/api/refer/", json.dumps({"facility_id": self.phc.pk}), content_type="application/json")
        self.assertTrue(res.json()["ok"])

    def test_worker_and_gov(self):
        self.login("worker")
        self.assertEqual(self.client.get("/worker/").status_code, 200)
        self.client.post(f"/worker/child/{self.tobi.pk}/vaccinate/")
        self.assertTrue(self.tobi.immunizations.filter(vaccine__code="PENTA1").exists())
        self.login("gov")
        self.assertEqual(self.client.get("/gov/").status_code, 200)
        csv = self.client.get("/gov/export.csv").content.decode()
        self.assertIn("Ibadan North", csv)

    def test_api_suppresses_small_counts(self):
        row = self.client.get("/api/v1/lgas/").json()["results"][0]
        self.assertEqual(row["enrolled"], "<5")  # 2 families < ANON_MIN_CELL

    def test_signup_requires_consent_and_delete_erases(self):
        res = self.client.post("/signup/", {"username": "new", "password1": "abc12345!", "password2": "abc12345!",
                                            "full_name": "New User", "language": "ha", "lga": self.lga.pk})
        self.assertEqual(res.status_code, 200)  # consent missing
        res = self.client.post("/signup/", {"username": "new", "password1": "abc12345!", "password2": "abc12345!",
                                            "full_name": "New User", "language": "ha", "lga": self.lga.pk, "consent": "on"})
        self.assertRedirects(res, "/home/")
        self.client.post("/profile/delete/")
        self.assertFalse(User.objects.filter(username="new").exists())
        self.assertFalse(Profile.objects.filter(full_name="New User").exists())
