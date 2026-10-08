"""Exercise the N-ATLaS client against a fake gateway that mimics the documented N-ATLAS-Kit routes."""

import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from alerts.engine import run_loop
from alerts.models import Alert
from navigator import natlas
from navigator.engine import respond
from navigator.models import VoiceClip
from navigator.voice import speakable, wav_to_mp3

from .test_lafiya import LafiyaTestCase

KEY = "test-key"


def make_wav(seconds=0.5, rate=16000):
    import io
    import math
    import struct
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(i / 8))) for i in range(int(seconds * rate))))
    return buf.getvalue()


WAV = make_wav()


class FakeGateway(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *args):
        pass

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "llm": "NCAIR1/N-ATLaS", "asr": ["ha", "ig", "yo", "en"]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        FakeGateway.requests.append((self.path, self.headers, body))
        if self.headers.get("Authorization") != f"Bearer {KEY}":
            return self._send(401, {"error": "Missing or invalid API key"})
        if self.path == "/v1/chat/completions":
            payload = json.loads(body)
            return self._send(200, {"choices": [{"message": {"content": f"N-ATLaS reply ({payload.get('language', '-')})"}}]})
        if self.path == "/v1/audio/speech":
            payload = json.loads(body)
            if not payload.get("input"):
                return self._send(400, {"error": "empty"})
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("X-Natlas-Voice", f"mms-tts-{payload.get('language')}")
            self.send_header("Content-Length", str(len(WAV)))
            self.end_headers()
            self.wfile.write(WAV)
            return
        if self.path == "/v1/audio/transcriptions":
            if b'name="file"' not in body:
                return self._send(400, {"error": "file required"})
            lang = body.split(b'name="language"\r\n\r\n')[1].split(b"\r\n")[0].decode()
            return self._send(200, {"text": f"transcript-{lang}"})
        self._send(404, {"error": "not found"})


class GatewayTests(LafiyaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGateway)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        super().tearDownClass()

    def gateway(self, key=KEY, base=None):
        return override_settings(NATLAS={"API_URL": base or self.base, "API_KEY": key, "MODEL": "NCAIR1/N-ATLaS", "TIMEOUT": 5})

    def setUp(self):
        FakeGateway.requests.clear()

    def test_endpoint_accepts_any_base_form(self):
        for base in (self.base, self.base + "/", self.base + "/v1", self.base + "/v1/chat/completions"):
            with self.gateway(base=base):
                self.assertEqual(natlas.endpoint("/v1/chat/completions"), self.base + "/v1/chat/completions")

    def test_health(self):
        with self.gateway():
            ok, details = natlas.health()
        self.assertTrue(ok)
        self.assertEqual(details["status"], "ok")
        with self.gateway(base="http://127.0.0.1:1"):
            self.assertFalse(natlas.health(timeout=1)[0])

    def test_navigator_uses_natlas_with_language_and_auth(self):
        with self.gateway():
            r = respond(self.funke, "Which vaccine does my baby need next?", language="yo")
        self.assertEqual(r["generated_by"], "n-atlas")
        self.assertEqual(r["reply"], "N-ATLaS reply (yo)")
        path, headers, body = FakeGateway.requests[-1]
        payload = json.loads(body)
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(payload["model"], "NCAIR1/N-ATLaS")
        self.assertIn("Tobi", payload["messages"][0]["content"])  # grounded facts reach the model
        self.assertIsNotNone(r["reminder"])  # actions still happen

    def test_pidgin_language_not_sent_to_gateway(self):
        with self.gateway():
            respond(self.funke, "Which vaccine my pikin need next?", language="pcm")
        self.assertNotIn("language", json.loads(FakeGateway.requests[-1][2]))

    def test_emergency_prefix_kept_when_model_answers(self):
        with self.gateway():
            r = respond(self.mama, "I am pregnant and bleeding", language="en")
        self.assertTrue(r["reply"].startswith("This may be a danger sign"))
        self.assertIn("N-ATLaS reply", r["reply"])

    def test_bad_key_or_down_gateway_falls_back_to_templates(self):
        with self.gateway(key="wrong"):
            r = respond(self.funke, "Which vaccine next?", language="en")
        self.assertEqual(r["generated_by"], "template")
        self.assertIn("Pentavalent 1", r["reply"])
        with self.gateway(base="http://127.0.0.1:1"):
            self.assertEqual(respond(self.funke, "Which vaccine next?", language="en")["generated_by"], "template")

    def test_transcribe_view(self):
        self.login("funke")
        audio = lambda: SimpleUploadedFile("voice.webm", b"\x1aE\xdf\xa3fake-webm", content_type="audio/webm")  # noqa: E731
        res = self.client.post("/navigator/api/transcribe/", {"audio": audio(), "language": "yo"})
        self.assertEqual(res.status_code, 503)  # not configured
        with self.gateway():
            res = self.client.post("/navigator/api/transcribe/", {"audio": audio(), "language": "yo"})
            self.assertEqual(res.json()["text"], "transcript-yo")
            res = self.client.post("/navigator/api/transcribe/", {"audio": audio(), "language": "pcm"})
            self.assertEqual(res.json()["text"], "transcript-en")  # Pidgin -> Nigerian-accented English ASR
        with self.gateway(key="wrong"):
            res = self.client.post("/navigator/api/transcribe/", {"audio": audio(), "language": "yo"})
            self.assertEqual(res.status_code, 502)

    def test_alerts_written_by_natlas(self):
        with self.gateway():
            run_loop(date.today(), refresh_weather=True, live=False)
        self.assertEqual(Alert.objects.get(profile=self.funke, kind="vaccine").generated_by, "template")  # off by default
        Alert.objects.all().delete()
        with self.gateway():
            run_loop(date.today(), refresh_weather=False, use_natlas=True)
        alert = Alert.objects.get(profile=self.funke, kind="vaccine")
        self.assertEqual(alert.generated_by, "n-atlas")
        self.assertEqual(alert.message, "N-ATLaS reply (yo)")

    # ---- voice in, voice out (POST /v1/audio/speech) ----
    def test_speakable_text(self):
        text = "📍 *Obasa PHC* — 1 km. https://www.openstreetmap.org/?mlat=7 Go today. " + "Ọmọ " * 400
        out = speakable(text)
        self.assertNotIn("http", out)
        self.assertNotIn("📍", out)
        self.assertNotIn("*", out)
        self.assertLessEqual(len(out), 780)

    def test_wav_to_mp3(self):
        mp3 = wav_to_mp3(WAV)
        self.assertTrue(mp3[:3] == b"ID3" or mp3[0] == 0xFF)
        self.assertLess(len(mp3), len(WAV))

    def test_web_answer_is_spoken_in_its_language(self):
        self.login("funke")
        with self.gateway():
            data = self.client.post("/navigator/api/ask/", json.dumps({"text": "Which vaccine next?", "language": "yo"}),
                                    content_type="application/json").json()
            res = self.client.post("/navigator/api/speak/", json.dumps({"message_id": data["message_id"]}),
                                   content_type="application/json").json()
        self.assertEqual(res["voice"], "mms-tts-yo")
        spoken = [json.loads(b) for p, _, b in FakeGateway.requests if p == "/v1/audio/speech"]
        self.assertEqual(spoken[-1]["language"], "yo")
        audio = self.client.get(res["url"])
        self.assertEqual(audio["Content-Type"], "audio/mpeg")
        # Second request reuses the stored clip
        with self.gateway():
            self.client.post("/navigator/api/speak/", json.dumps({"message_id": data["message_id"]}),
                             content_type="application/json")
        self.assertEqual(VoiceClip.objects.count(), 1)

    def test_cannot_speak_someone_elses_message(self):
        self.login("funke")
        with self.gateway():
            data = self.client.post("/navigator/api/ask/", json.dumps({"text": "hello"}),
                                    content_type="application/json").json()
        self.login("mama")
        res = self.client.post("/navigator/api/speak/", json.dumps({"message_id": data["message_id"]}),
                               content_type="application/json")
        self.assertEqual(res.status_code, 404)

    def test_no_gateway_means_browser_fallback(self):
        self.login("funke")
        data = self.client.post("/navigator/api/ask/", json.dumps({"text": "hello"}), content_type="application/json").json()
        res = self.client.post("/navigator/api/speak/", json.dumps({"message_id": data["message_id"]}),
                               content_type="application/json")
        self.assertEqual(res.status_code, 503)
