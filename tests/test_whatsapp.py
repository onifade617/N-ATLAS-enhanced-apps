"""WhatsApp voice-note channel, validation evidence and challenge mode."""

import base64
import hashlib
import hmac
import io
import json
import threading
import urllib.parse
from datetime import date
from http.server import ThreadingHTTPServer

from django.core.management import call_command
from django.test import override_settings

from alerts.engine import run_loop
from alerts.models import Alert
from core.models import Profile
from dashboard.evidence import summary
from navigator import whatsapp
from navigator.models import Message, VoiceClip, WhatsAppContact
from navigator.whatsapp_texts import LANGUAGE_MENU

from .test_lafiya import LafiyaTestCase
from .test_natlas_gateway import KEY, FakeGateway

SID, TOKEN = "AC123", "twilio-secret"
AUDIO = b"OggS\x00fake-whatsapp-opus"


class FakeTwilioAndGateway(FakeGateway):
    asr_text = "which vaccine does my baby need next"
    sent = []

    def do_GET(self):
        if self.path == "/media/1":  # Twilio media URL: needs Basic auth, then redirects to a CDN host
            if not (self.headers.get("Authorization") or "").startswith("Basic "):
                return self._send(401, {"error": "auth required"})
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{self.server.server_port}/cdn/1")
            self.end_headers()
            return
        if self.path == "/cdn/1":  # pre-signed CDN URL rejects a second auth mechanism
            if self.headers.get("Authorization"):
                return self._send(400, {"error": "only one auth mechanism allowed"})
            self.send_response(200)
            self.send_header("Content-Type", "audio/ogg")
            self.send_header("Content-Length", str(len(AUDIO)))
            self.end_headers()
            self.wfile.write(AUDIO)
            return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/2010-04-01/Accounts/"):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            expected = "Basic " + base64.b64encode(f"{SID}:{TOKEN}".encode()).decode()
            if self.headers.get("Authorization") != expected:
                return self._send(401, {"error": "bad auth"})
            FakeTwilioAndGateway.sent.append(dict(urllib.parse.parse_qsl(body.decode())))
            return self._send(201, {"sid": "SM1"})
        if self.path == "/v1/audio/transcriptions":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            assert AUDIO in body, "voice note bytes must reach the ASR"
            FakeGateway.requests.append((self.path, self.headers, body))
            return self._send(200, {"text": FakeTwilioAndGateway.asr_text})
        super().do_POST()


class WhatsAppTests(LafiyaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeTwilioAndGateway)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        super().tearDownClass()

    def setUp(self):
        FakeTwilioAndGateway.sent.clear()
        whatsapp.OUTBOX.clear()
        self.overrides = override_settings(
            NATLAS={"API_URL": self.base, "API_KEY": KEY, "MODEL": "NCAIR1/N-ATLaS", "TIMEOUT": 5},
            TWILIO={"ACCOUNT_SID": SID, "AUTH_TOKEN": TOKEN, "WHATSAPP_FROM": "whatsapp:+14155238886",
                    "VALIDATE_SIGNATURE": True},
            WHATSAPP_ASYNC=False,
            PUBLIC_BASE_URL="https://lafiya.example.ngrok.app",
        )
        self.overrides.enable()
        self.old_api = whatsapp.TWILIO_API
        whatsapp.TWILIO_API = self.base + "/2010-04-01/Accounts/{sid}/Messages.json"

    def tearDown(self):
        whatsapp.TWILIO_API = self.old_api
        self.overrides.disable()

    # -- helpers
    def post(self, phone="+2348031234567", sign=True, **fields):
        data = {"From": f"whatsapp:{phone}", "ProfileName": "Bisi", "NumMedia": "0", "Body": "", **fields}
        url = "https://lafiya.example.ngrok.app/whatsapp/twilio/"
        payload = url + "".join(k + v for k, v in sorted(data.items()))
        sig = base64.b64encode(hmac.new(TOKEN.encode(), payload.encode(), hashlib.sha1).digest()).decode()
        return self.client.post("/whatsapp/twilio/", data, HTTP_X_TWILIO_SIGNATURE=sig if sign else "bad")

    def last_reply(self):
        """Last text message (a voice note is followed by a separate audio-only reply)."""
        return next(m["Body"] for m in reversed(FakeTwilioAndGateway.sent) if "Body" in m)

    def onboard(self, phone="+2348031234567"):
        self.post(phone, Body="hi")
        self.post(phone, Body="3")  # Yoruba
        self.post(phone, Body="Bẹ́ẹ̀ni")
        self.post(phone, Body="I live in Ibadan North")
        return WhatsAppContact.objects.get(phone=phone)

    # -- tests
    def test_rejects_bad_signature(self):
        self.assertEqual(self.post(sign=False, Body="hi").status_code, 403)
        self.assertEqual(self.post(Body="hi").status_code, 200)

    def test_onboarding_language_consent_location(self):
        self.post(Body="hi")
        self.assertEqual(self.last_reply(), LANGUAGE_MENU)
        self.post(Body="3")
        self.assertIn("BẸ́Ẹ̀NI", self.last_reply())  # consent asked in Yoruba
        self.assertFalse(Profile.objects.filter(phone="+2348031234567").exists())  # nothing stored before consent
        self.post(Body="Bẹ́ẹ̀ni")
        profile = Profile.objects.get(phone="+2348031234567")
        self.assertTrue(profile.consent_given)
        self.assertFalse(profile.is_demo)
        self.post(Body="I live in Ibadan North")
        profile.refresh_from_db()
        self.assertEqual(profile.lga, self.lga)
        self.assertIn("Ibadan North", self.last_reply())
        sent = FakeTwilioAndGateway.sent[-1]
        self.assertEqual((sent["From"], sent["To"]), ("whatsapp:+14155238886", "whatsapp:+2348031234567"))

    def test_declining_consent_stores_nothing(self):
        self.post(Body="hi")
        self.post(Body="2")
        self.post(Body="a'a")
        self.assertFalse(WhatsAppContact.objects.exists())
        self.assertFalse(Profile.objects.filter(phone="+2348031234567").exists())

    def test_voice_note_transcribed_by_natlas_and_answered(self):
        contact = self.onboard()
        FakeGateway.requests.clear()
        self.post(NumMedia="1", MediaUrl0=self.base + "/media/1", MediaContentType0="audio/ogg")
        asr = [r for r in FakeGateway.requests if r[0] == "/v1/audio/transcriptions"]
        self.assertEqual(len(asr), 1)
        self.assertIn(b'name="language"\r\n\r\nyo', asr[0][2])  # user's language sent to the ASR
        reply = self.last_reply()
        self.assertIn("which vaccine does my baby need next", reply)  # transcript echoed back
        self.assertIn("N-ATLaS reply (yo)", reply)  # answer written by N-ATLaS
        self.assertIn("📍", reply)  # nearest facility
        q = Message.objects.filter(conversation__profile=contact.profile, role="user").last()
        self.assertEqual((q.channel, q.input_mode, q.asr_engine), ("whatsapp", "voice", "n-atlas"))

    def test_location_pin_sets_nearest_lga(self):
        contact = self.onboard()
        self.post(Latitude="7.41", Longitude="3.91")
        contact.profile.refresh_from_db()
        self.assertEqual(contact.profile.lga, self.lga)
        self.assertAlmostEqual(contact.profile.latitude, 7.41)

    def test_stop_erases_everything(self):
        contact = self.onboard()
        self.post(Body="hello there, which vaccine next?")
        pid = contact.profile.id
        self.post(Body="STOP")
        self.assertFalse(Profile.objects.filter(id=pid).exists())
        self.assertFalse(Message.objects.filter(conversation__profile_id=pid).exists())
        self.assertFalse(WhatsAppContact.objects.exists())

    def test_chw_enrolled_household_is_recognised(self):
        enrolled = Profile.objects.create(full_name="Ngozi", phone="0803 123 4568", language="ig", lga=self.lga,
                                          consent_given=True)
        self.post(phone="+2348031234568", Body="Which vaccine next?")
        contact = WhatsAppContact.objects.get(phone="+2348031234568")
        self.assertEqual(contact.profile, enrolled)
        self.assertEqual(contact.state, "ready")
        self.assertTrue(FakeTwilioAndGateway.sent[-1]["Body"].startswith("N-ATLaS reply (ig)"))  # in Igbo, no onboarding

    def test_new_alerts_pushed_to_active_whatsapp_users(self):
        contact = self.onboard()
        from core.models import Child

        Child.objects.create(caregiver=contact.profile, name="Ife", sex="F", date_of_birth=date.today())
        run_loop(date.today(), refresh_weather=True, live=False)
        alert = Alert.objects.get(profile=contact.profile, kind="vaccine")
        self.assertEqual(alert.channel, "whatsapp")
        self.assertTrue(any("Ife" in m["Body"] for m in FakeTwilioAndGateway.sent))

    # ---- voice in, voice out ----
    def test_voice_note_gets_voice_reply_in_same_language(self):
        self.onboard()  # Yoruba
        self.post(NumMedia="1", MediaUrl0=self.base + "/media/1", MediaContentType0="audio/ogg")
        text_msg, voice_msg = FakeTwilioAndGateway.sent[-2], FakeTwilioAndGateway.sent[-1]
        self.assertIn("N-ATLaS reply (yo)", text_msg["Body"])
        self.assertTrue(voice_msg["MediaUrl"].startswith("https://lafiya.example.ngrok.app/voice/"))
        self.assertTrue(voice_msg["MediaUrl"].endswith(".mp3"))
        clip = VoiceClip.objects.get()
        self.assertEqual((clip.language, clip.content_type), ("yo", "audio/mpeg"))
        self.assertEqual(self.client.get(voice_msg["MediaUrl"].replace("https://lafiya.example.ngrok.app", "")).status_code, 200)

    def test_text_question_gets_text_only(self):
        self.onboard()
        self.post(Body="Where is the nearest clinic?")
        self.assertNotIn("MediaUrl", FakeTwilioAndGateway.sent[-1])
        self.assertFalse(VoiceClip.objects.exists())


class EvidenceTests(LafiyaTestCase):
    def test_evidence_counts_real_users_only(self):
        from navigator.engine import ask

        demo = Profile.objects.create(full_name="Demo", lga=self.lga, consent_given=True, is_demo=True)
        ask(demo, "which vaccine next?")
        ask(self.funke, "which vaccine next?", channel="whatsapp", input_mode="voice", asr_engine="n-atlas")
        ask(self.mama, "my child has fever")
        s = summary()
        self.assertEqual((s["total"], s["users"], s["voice"], s["voice_natlas_asr"]), (2, 2, 1, 1))
        self.assertEqual(dict(s["by_channel"]), {"whatsapp": 1, "web": 1})

        out = io.StringIO()
        call_command("export_evidence", "-o", str(self._tmp("e.csv")), stdout=out)
        csv_text = self._tmp("e.csv").read_text(encoding="utf-8")
        self.assertIn("user_ref", csv_text)
        self.assertNotIn("which vaccine", csv_text)  # no message text unless --with-text
        self.assertIn("2/50 real interactions", out.getvalue())

        self.login("gov")
        self.assertContains(self.client.get("/gov/"), "real user interactions")
        self.assertEqual(self.client.get("/gov/evidence.csv").status_code, 200)

    def _tmp(self, name):
        import tempfile
        from pathlib import Path

        if not hasattr(self, "_dir"):
            self._dir = Path(tempfile.mkdtemp())
        return self._dir / name

    @override_settings(CHALLENGE_MODE=True)
    def test_challenge_mode_flag_reaches_chat(self):
        self.login("funke")
        self.assertContains(self.client.get("/navigator/"), "window.challengeMode = true")

    def test_web_voice_evidence_recorded(self):
        self.login("funke")
        self.client.post("/navigator/api/ask/", json.dumps({"text": "which vaccine?", "input_mode": "voice", "asr": "n-atlas"}),
                         content_type="application/json")
        q = Message.objects.filter(role="user").last()
        self.assertEqual((q.channel, q.input_mode, q.asr_engine), ("web", "voice", "n-atlas"))
