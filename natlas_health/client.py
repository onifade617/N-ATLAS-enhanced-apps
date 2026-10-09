"""NatlasClient: a small, dependency-free client for the N-ATLaS gateway (N-ATLAS-Kit).

Gateway routes (https://natlas-docs.vercel.app/gateway):
  GET  /health                    no auth; LLM + ASR upstream status (503 = gateway up, an upstream down)
  POST /v1/chat/completions       Bearer auth; OpenAI-style JSON plus "language"
  POST /v1/audio/transcriptions   Bearer auth; multipart: file + language (ha/ig/yo/en)
  POST /v1/audio/speech           Bearer auth; JSON {input, language} -> audio/wav (MMS-TTS voices)

Any OpenAI-compatible server running N-ATLaS (e.g. ``vllm serve NCAIR1/N-ATLaS``) works for chat.

    from natlas_health import NatlasClient
    client = NatlasClient.from_env()                       # NATLAS_BASE_URL, NATLAS_API_KEY, ...
    print(client.chat("Sannu! Yaya kake?", language="ha").text)
"""

import json
import os
import socket
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field

from . import languages
from .errors import (
    AuthenticationError,
    BadRequestError,
    FeatureNotEnabledError,
    InvalidResponseError,
    NatlasError,
    NotConfiguredError,
    UnavailableError,
)

DEFAULT_MODEL = "NCAIR1/N-ATLaS"
USER_AGENT = "natlas-health-python/0.1"


@dataclass
class ChatResponse:
    text: str
    model: str
    latency_ms: int
    raw: dict = field(repr=False)


@dataclass
class Transcription:
    text: str
    language: str  # the ASR model actually used (Pidgin -> "en")
    latency_ms: int
    raw: dict = field(repr=False)


@dataclass
class Speech:
    audio: bytes = field(repr=False)
    content_type: str
    voice: str
    latency_ms: int


@dataclass
class HealthStatus:
    ok: bool
    details: object  # JSON body from /health, or an error string

    def __bool__(self):
        return self.ok


def normalize_base_url(url):
    """Accept a gateway base with or without a trailing /, /v1 or /v1/chat/completions."""
    base = (url or "").strip().rstrip("/")
    for suffix in ("/chat/completions", "/v1"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base


class NatlasClient:
    def __init__(self, base_url=None, api_key=None, model=DEFAULT_MODEL, timeout=60, retries=0, retry_wait=5.0):
        """
        base_url   gateway URL, e.g. https://<workspace>--natlas-serve-natlasservice-serve.modal.run
        api_key    one of the gateway's NATLAS_API_KEYS (not your Hugging Face token)
        timeout    seconds per request; a Modal cold start can take several minutes
        retries    extra attempts after an UnavailableError (cold start, 502/503/504, timeout)
        """
        self.base_url = normalize_base_url(base_url)
        self.api_key = api_key or ""
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout
        self.retries = retries
        self.retry_wait = retry_wait

    @classmethod
    def from_env(cls, **overrides):
        """Build a client from NATLAS_BASE_URL (or NATLAS_API_URL), NATLAS_API_KEY, NATLAS_MODEL, NATLAS_TIMEOUT."""
        opts = {
            "base_url": os.environ.get("NATLAS_BASE_URL") or os.environ.get("NATLAS_API_URL", ""),
            "api_key": os.environ.get("NATLAS_API_KEY", ""),
            "model": os.environ.get("NATLAS_MODEL") or DEFAULT_MODEL,
            "timeout": int(os.environ.get("NATLAS_TIMEOUT") or 60),
        }
        opts.update(overrides)
        return cls(**opts)

    @property
    def configured(self):
        return bool(self.base_url)

    def url(self, path):
        return self.base_url + path

    def __repr__(self):
        return f"NatlasClient(base_url={self.base_url!r}, model={self.model!r})"

    # ---- transport -----------------------------------------------------------
    def _request(self, path, body=None, content_type=None, method="POST", timeout=None):
        if not self.configured:
            raise NotConfiguredError("No N-ATLaS gateway URL. Pass base_url= or set NATLAS_BASE_URL.")
        attempt = 0
        while True:
            try:
                return self._send(path, body, content_type, method, timeout or self.timeout)
            except UnavailableError:
                if attempt >= self.retries:
                    raise
                attempt += 1
                time.sleep(self.retry_wait * attempt)

    def _send(self, path, body, content_type, method, timeout):
        headers = {"User-Agent": USER_AGENT}
        if content_type:
            headers["Content-Type"] = content_type
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.url(path), data=body, headers=headers, method=method)
        started = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                return data, resp.headers, int((time.monotonic() - started) * 1000)
        except urllib.error.HTTPError as exc:
            raise _http_error(exc) from None
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
            reason = getattr(exc, "reason", exc)
            raise UnavailableError(f"Cannot reach the N-ATLaS gateway at {self.base_url}: {reason}") from None

    def _json(self, path, payload, timeout=None):
        data, headers, latency = self._request(path, json.dumps(payload).encode(), "application/json", timeout=timeout)
        return _parse_json(data), headers, latency

    # ---- API -----------------------------------------------------------------
    def health(self, timeout=10):
        """GET /health. Never raises: returns HealthStatus(ok, details)."""
        if not self.configured:
            return HealthStatus(False, "NATLAS_BASE_URL is not set")
        try:
            data, _, _ = self._send("/health", None, None, "GET", timeout)
            return HealthStatus(True, _parse_json(data))
        except NatlasError as exc:
            return HealthStatus(False, exc.body if isinstance(exc.body, dict) else str(exc))

    def chat(self, messages, language=None, temperature=0.3, max_tokens=500, **extra):
        """Chat completion. ``messages`` is an OpenAI-style list, or a plain string for a single user turn.

        ``language`` (en/ha/ig/yo/pcm) selects the gateway's chat template; codes it does not know are left out.
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **extra,
        }
        lang = languages.chat_language(language)
        if lang:
            payload["language"] = lang  # the gateway applies its chat template, then strips it
        data, _, latency = self._json("/v1/chat/completions", payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise InvalidResponseError("Chat response has no choices[0].message.content", body=data) from None
        return ChatResponse(text=(text or "").strip(), model=data.get("model", self.model), latency_ms=latency, raw=data)

    def transcribe(self, audio, filename="audio.wav", content_type=None, language="en"):
        """Speech-to-text with the per-language Whisper models. ``audio`` is bytes or a file path."""
        if isinstance(audio, (str, os.PathLike)):
            filename = os.path.basename(audio) if filename == "audio.wav" else filename
            with open(audio, "rb") as fh:
                audio = fh.read()
        if not audio:
            raise BadRequestError("No audio to transcribe")
        lang = languages.asr_language(language)
        boundary = uuid.uuid4().hex
        parts = []
        for name, value in (("language", lang), ("response_format", "json")):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n".encode()
        )
        parts.append(audio)
        parts.append(f"\r\n--{boundary}--\r\n".encode())
        data, _, latency = self._request(
            "/v1/audio/transcriptions", b"".join(parts), f"multipart/form-data; boundary={boundary}"
        )
        data = _parse_json(data)
        return Transcription(text=(data.get("text") or "").strip(), language=lang, latency_ms=latency, raw=data)

    def speak(self, text, language="en"):
        """Text-to-speech (MMS-TTS voices). Returns Speech with WAV bytes. Input is limited to ~800 characters."""
        if not text or not text.strip():
            raise BadRequestError("No text to speak")
        payload = {"input": text, "language": languages.tts_language(language)}
        data, headers, latency = self._request(
            "/v1/audio/speech", json.dumps(payload).encode(), "application/json"
        )
        return Speech(
            audio=data, content_type=headers.get("Content-Type", "audio/wav"),
            voice=headers.get("X-Natlas-Voice", ""), latency_ms=latency,
        )


def _parse_json(data):
    try:
        return json.loads(data)
    except (ValueError, TypeError):
        raise InvalidResponseError("Gateway did not return JSON", body=data[:500] if data else data) from None


def _error_detail(body):
    """The message in a gateway error: FastAPI {"detail"}, vLLM {"message"}, OpenAI {"error": {"message"}}."""
    if not isinstance(body, dict):
        return None
    for key in ("detail", "message", "error"):
        value = body.get(key)
        if isinstance(value, dict):
            value = value.get("message")
        if isinstance(value, str) and value:
            return value
    return None


def _http_error(exc):
    try:
        body = json.load(exc)
    except Exception:
        body = None
    detail = _error_detail(body)
    msg = f"HTTP {exc.code}" + (f": {detail}" if detail else "")
    if exc.code in (401, 403):
        cls = AuthenticationError
    elif exc.code == 501:
        cls = FeatureNotEnabledError
    elif exc.code in (502, 503, 504) or exc.code == 429:
        cls = UnavailableError
    elif 400 <= exc.code < 500:
        cls = BadRequestError
    else:
        cls = NatlasError
    return cls(msg, status=exc.code, body=body)
