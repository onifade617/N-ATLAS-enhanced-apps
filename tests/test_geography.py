"""All 36 states + FCT and 774 LGAs; batched national weather; LGA matching."""

import json
import threading
import urllib.parse
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from django.test import TestCase, override_settings

from climateguard import weather
from climateguard.models import WeatherDay
from core.geography import load_geography
from core.models import LGA, Profile, State
from navigator.whatsapp import match_lga


class GeographyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # A pre-existing state/LGA with an old spelling must be updated, not duplicated.
        oyo = State.objects.create(name="Oyo", code="OY")
        cls.old = LGA.objects.create(state=oyo, name="Ibadan South-West", latitude=7.0, longitude=3.0)
        cls.result = load_geography()

    def test_all_states_and_lgas(self):
        self.assertEqual(State.objects.count(), 37)
        self.assertEqual(LGA.objects.count(), 774)
        self.assertFalse(LGA.objects.filter(pcode__isnull=True).exists())
        self.assertEqual(State.objects.get(code="FC").lgas.count(), 6)
        self.assertEqual(State.objects.get(code="KN").lgas.count(), 44)
        self.assertEqual(State.objects.get(code="LA").lgas.count(), 20)

    def test_existing_records_updated_and_spellings_corrected(self):
        self.old.refresh_from_db()
        self.assertEqual(self.old.name, "Ibadan South West")
        self.assertIsNotNone(self.old.pcode)
        self.assertTrue(LGA.objects.filter(name="Obio/Akpor", state__code="RI").exists())
        self.assertTrue(LGA.objects.filter(name="Port Harcourt").exists())
        self.assertEqual(load_geography()["lgas_created"], 0)  # idempotent

    def test_coordinates_inside_nigeria(self):
        for lga in LGA.objects.all():
            self.assertTrue(4.0 <= lga.latitude <= 14.0 and 2.6 <= lga.longitude <= 14.7, lga)

    def test_signup_any_state(self):
        maiduguri = LGA.objects.get(name="Maiduguri", state__code="BO")
        page = self.client.get("/signup/").content.decode()
        self.assertIn('label="Borno"', page)
        self.assertIn("data-lga-picker", page)
        res = self.client.post("/signup/", {"username": "fatima", "password1": "abc12345!", "password2": "abc12345!",
                                            "full_name": "Fatima Ali", "language": "ha", "lga": maiduguri.pk,
                                            "consent": "on"})
        self.assertRedirects(res, "/home/")
        self.assertEqual(Profile.objects.get(full_name="Fatima Ali").lga, maiduguri)

    def test_match_lga_whole_words_and_ambiguity(self):
        self.assertEqual(match_lga("I live in Ibadan North").name, "Ibadan North")
        self.assertEqual(match_lga("ibadan north east").name, "Ibadan North East")
        self.assertIsNone(match_lga("Surulere"))  # in both Lagos and Oyo -> ask again
        self.assertEqual(match_lga("Surulere, Lagos").state.code, "LA")
        self.assertEqual(match_lga("Obio Akpor").name, "Obio/Akpor")
        self.assertIsNone(match_lga("my name is Obinna"))  # no false match on "Obi"


class FakeOpenMeteo(BaseHTTPRequestHandler):
    calls = 0
    fail_first = True

    def log_message(self, *args):
        pass

    def do_GET(self):
        FakeOpenMeteo.calls += 1
        if FakeOpenMeteo.fail_first:
            FakeOpenMeteo.fail_first = False
            self.send_response(429)
            self.end_headers()
            return
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        n = len(q["latitude"][0].split(","))
        start = date.today() - timedelta(days=21)
        days = [(start + timedelta(days=i)).isoformat() for i in range(28)]
        item = {"daily": {"time": days, "temperature_2m_max": [31] * 28, "temperature_2m_min": [23] * 28,
                          "apparent_temperature_max": [34] * 28, "precipitation_sum": [5] * 28,
                          "relative_humidity_2m_mean": [80] * 28}}
        body = json.dumps([item] * n if n > 1 else item).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


class NationalWeatherTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_geography()

    def test_batched_live_weather_with_rate_limit_retry(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenMeteo)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        old = weather.OPEN_METEO_URL, weather.RATE_LIMIT_WAIT
        weather.OPEN_METEO_URL, weather.RATE_LIMIT_WAIT = f"http://127.0.0.1:{server.server_port}/v1/forecast", 0
        try:
            with override_settings(CLIMATE_LIVE_WEATHER=True):
                lgas = list(LGA.objects.all()[:120])
                sources = weather.ingest_lgas(lgas)
        finally:
            weather.OPEN_METEO_URL, weather.RATE_LIMIT_WAIT = old
            server.shutdown()
            server.server_close()
        self.assertEqual(sources, {"open-meteo": 120})
        self.assertEqual(FakeOpenMeteo.calls, 4)  # 3 batches of <=50 + one 429 retry
        self.assertEqual(WeatherDay.objects.count(), 120 * 28)

    def test_national_loop_offline(self):
        from alerts.engine import sense

        self.assertEqual(sense(live=False), {"simulated": 774})
