"""Test N-ATLaS apps without a GPU.

MockClient     an offline NatlasClient: same API and parsing, canned answers, no network. Use it in unit tests,
               CI and the playground's --mock mode so you don't spend GPU credit while wiring things up.
FakeGateway    a local HTTP server that mimics the gateway routes, status codes and error bodies (FastAPI
               {"detail": ...}) of N-ATLAS-Kit's natlas_serve.gateway, for end-to-end tests of code that builds its
               own NatlasClient from a URL. Unlike the real gateway it accepts any bytes as audio (no ffmpeg):

    with FakeGateway(api_key="test-key") as gw:
        client = NatlasClient(gw.url, api_key="test-key")
        client.chat("hello", language="ha").text      # 'N-ATLaS reply (ha)'
        gw.requests[-1]                                # (path, headers, body) for assertions
"""

import io
import json
import math
import re
import struct
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .client import NatlasClient
from .errors import AuthenticationError


def make_wav(seconds=0.5, rate=16000):
    """A short 16-bit mono tone, handy as fake speech."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(i / 8))) for i in range(int(seconds * rate))))
    return buf.getvalue()


WAV = make_wav()


def _fake_reply(payload):
    return f"N-ATLaS reply ({payload.get('language', '-')})"


def _form_field(body, name):
    m = re.search(rb'name="' + name.encode() + rb'"\r\n\r\n([^\r]*)\r\n', body)
    return m.group(1).decode() if m else ""


ASR_LANGUAGES = ("ha", "ig", "yo", "en")


class GatewayHandler(BaseHTTPRequestHandler):
    """Request handler behind FakeGateway; subclass it to add routes (e.g. a fake Twilio) on the same server."""

    def log_message(self, *args):
        pass

    def _send(self, code, body, content_type="application/json", headers=None):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "version": "fake", "llm": {"model": "NCAIR1/N-ATLaS", "status": "ok"},
                                    "asr": {"languages": list(ASR_LANGUAGES), "status": "ok", "mode": "local"}})
        self._send(404, {"detail": "Not Found"})

    def do_POST(self):
        gw = self.server.gateway
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        gw.requests.append((self.path, self.headers, body))
        if gw.api_key and self.headers.get("Authorization") != f"Bearer {gw.api_key}":
            return self._send(401, {"detail": "Missing or invalid API key. Send 'Authorization: Bearer <key>'."})
        if self.path == "/v1/chat/completions":
            payload = json.loads(body)
            return self._send(200, {"model": payload.get("model"),
                                    "choices": [{"message": {"role": "assistant", "content": gw.reply(payload)}}]})
        if self.path == "/v1/audio/speech":
            payload = json.loads(body)
            if not gw.speech:
                return self._send(501, {"detail": "Spoken replies are not enabled on this gateway."})
            if not (payload.get("input") or "").strip():
                return self._send(400, {"detail": "Nothing to say."})
            voice = payload.get("language") if payload.get("language") in ASR_LANGUAGES else "en"
            return self._send(200, WAV, "audio/wav", {"X-Natlas-Voice": voice})
        if self.path == "/v1/audio/transcriptions":
            if b'name="file"' not in body:
                return self._send(422, {"detail": [{"loc": ["body", "file"], "msg": "Field required"}]})
            lang = _form_field(body, "language")
            if lang not in ASR_LANGUAGES:
                return self._send(400, {"detail": f"Unsupported language {lang!r}. Pass one of: ha, ig, yo, en."})
            return self._send(200, {"text": f"transcript-{lang}"})
        self._send(404, {"detail": "Not Found"})


class FakeGateway:
    """Local stand-in for the N-ATLAS-Kit gateway. ``reply(payload) -> str`` customises chat answers."""

    def __init__(self, api_key="test-key", reply=_fake_reply, speech=True, host="127.0.0.1", port=0,
                 handler=GatewayHandler):
        self.api_key = api_key
        self.reply = reply
        self.speech = speech
        self.requests = []
        self.server = ThreadingHTTPServer((host, port), handler)
        self.server.gateway = self
        self.url = f"http://{host}:{self.server.server_port}"
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


class MockClient(NatlasClient):
    """Offline NatlasClient. Chat answers echo the first FACT so grounded wiring is visible; ``reply`` overrides."""

    def __init__(self, reply=None, api_key="mock", **kwargs):
        super().__init__(base_url="mock://n-atlas", api_key=api_key, **kwargs)
        self.reply = reply
        self.requests = []

    def _send(self, path, body, content_type, method, timeout):
        self.requests.append((path, body))
        if path == "/health":
            return json.dumps({"status": "ok", "mock": True}).encode(), {}, 0
        if not self.api_key:
            raise AuthenticationError("HTTP 401: Missing or invalid API key", status=401)
        if path == "/v1/chat/completions":
            payload = json.loads(body)
            text = self.reply(payload) if self.reply else self._default_reply(payload)
            return json.dumps({"model": self.model, "choices": [{"message": {"content": text}}]}).encode(), {}, 1
        if path == "/v1/audio/transcriptions":
            return json.dumps({"text": f"mock transcript ({_form_field(body, 'language')})"}).encode(), {}, 1
        if path == "/v1/audio/speech":
            lang = json.loads(body).get("language")
            return WAV, {"Content-Type": "audio/wav", "X-Natlas-Voice": f"mock-{lang}"}, 1
        raise AssertionError(f"MockClient has no route {path}")

    @staticmethod
    def _default_reply(payload):
        system = payload["messages"][0]["content"] if payload["messages"][0]["role"] == "system" else ""
        block = system.split("FACTS:\n", 1)[1].split("\n\n")[0] if "FACTS:\n" in system else ""
        facts = [line[2:] for line in block.split("\n") if line.startswith("- ")]
        lang = payload.get("language", "-")
        first = facts[0] if facts else payload["messages"][-1]["content"]
        return f"(mock N-ATLaS, {lang}) {first}"
