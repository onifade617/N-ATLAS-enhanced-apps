"""Client for the N-ATLaS gateway (N-ATLAS-Kit) or any OpenAI-compatible server running N-ATLaS.

Gateway routes used (see https://natlas-docs.vercel.app/gateway):
  GET  /health                    - no auth, reports LLM + ASR upstream status
  POST /v1/chat/completions       - Bearer auth, OpenAI-style JSON plus "language"
  POST /v1/audio/transcriptions   - Bearer auth, multipart: file + language (ha/ig/yo/en)

Configure with NATLAS_BASE_URL (or NATLAS_API_URL), NATLAS_API_KEY and NATLAS_MODEL.
If unconfigured or unreachable (e.g. a cold start), callers get ``None`` and Lafiya
falls back to its grounded templates / browser speech, so the product never breaks.
"""

import json
import logging
import urllib.error
import urllib.request
import uuid

from django.conf import settings

from core.models import LANGUAGE_NAMES

log = logging.getLogger(__name__)

# Languages the gateway's chat template and ASR models understand. Pidgin has no
# dedicated ASR model, so it is transcribed with the Nigerian-accented English model.
GATEWAY_LANGUAGES = {"en", "ha", "ig", "yo"}
ASR_LANGUAGE = {"en": "en", "ha": "ha", "ig": "ig", "yo": "yo", "pcm": "en"}

SYSTEM_PROMPT = """You are Lafiya, a trusted Community Health & Care Navigator for Nigerian families, built on N-ATLaS.
Rules:
- Reply ONLY in {language}. Use simple, warm, culturally appropriate words a mother or community health worker can act on.
- Ground every statement in the FACTS and GUIDANCE provided. Do not invent dates, facilities, vaccines or numbers.
- You educate and refer. You NEVER diagnose, prescribe doses, or tell someone they do not need care.
- If any danger sign is mentioned, tell them to go to the nearest health facility immediately or call 112.
- Use only the medical facts given (e.g. what each vaccine protects against). If something is not in the FACTS, do not guess.
- Never invent addresses, phone numbers, prices or placeholders like [address].
- If no phone number is given, do not tell them to call. Never promise to do something later (you cannot follow up).
- If facility hours are "not confirmed", say it is usually open at this time but the hours are not confirmed - never say it is definitely open.
- Plain text only: no markdown, no bullet points or numbered lists, no headings - replies are sent on WhatsApp and read aloud.
- At most 4 short sentences, then one clear next step."""


def is_configured():
    return bool(settings.NATLAS["API_URL"])


def endpoint(path):
    """Join the configured base URL and a gateway path, accepting bases with or without /v1."""
    base = settings.NATLAS["API_URL"].rstrip("/")
    for suffix in ("/chat/completions", "/v1"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base + path


def _headers(extra=None):
    headers = dict(extra or {})
    if settings.NATLAS["API_KEY"]:
        headers["Authorization"] = f"Bearer {settings.NATLAS['API_KEY']}"
    return headers


def _post(path, body, content_type, timeout):
    req = urllib.request.Request(
        endpoint(path), data=body, headers=_headers({"Content-Type": content_type}), method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def chat(messages, language=None, temperature=0.3, max_tokens=500):
    """Send chat messages to N-ATLaS. Returns the reply text or None on failure."""
    if not is_configured():
        return None
    payload = {
        "model": settings.NATLAS["MODEL"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if language in GATEWAY_LANGUAGES:
        payload["language"] = language  # the gateway uses it for the chat template, then strips it
    try:
        data = _post("/v1/chat/completions", json.dumps(payload).encode(), "application/json", settings.NATLAS["TIMEOUT"])
        return data["choices"][0]["message"]["content"].strip() or None
    except Exception as exc:
        log.warning("N-ATLaS chat failed: %s", exc)
        return None


def transcribe(audio_bytes, filename, content_type, language):
    """Speech-to-text through the gateway's per-language Whisper models. Returns text or None."""
    if not is_configured() or not audio_bytes:
        return None
    boundary = uuid.uuid4().hex
    lang = ASR_LANGUAGE.get(language, "en")
    parts = []
    for name, value in (("language", lang), ("response_format", "json")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n".encode()
    )
    parts.append(audio_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    try:
        data = _post(
            "/v1/audio/transcriptions", b"".join(parts), f"multipart/form-data; boundary={boundary}",
            settings.NATLAS["TIMEOUT"],
        )
        return (data.get("text") or "").strip() or None
    except Exception as exc:
        log.warning("N-ATLaS transcription failed: %s", exc)
        return None


def speak(text, language):
    """Text-to-speech via the gateway's POST /v1/audio/speech (MMS-TTS voices for Hausa, Igbo, Yoruba,
    English; Pidgin is read with the English voice). Returns (wav_bytes, voice_name) or None."""
    if not is_configured() or not text:
        return None
    body = json.dumps({"input": text, "language": language}).encode()
    req = urllib.request.Request(
        endpoint("/v1/audio/speech"), data=body, method="POST",
        headers=_headers({"Content-Type": "application/json"}),
    )
    try:
        with urllib.request.urlopen(req, timeout=settings.NATLAS["TIMEOUT"]) as resp:
            return resp.read(), resp.headers.get("X-Natlas-Voice", "")
    except Exception as exc:  # 501 = speech not enabled on this gateway
        log.warning("N-ATLaS speech failed: %s", exc)
        return None


def health(timeout=10):
    """GET /health (no key needed). Returns (ok, details) — details is the JSON body or an error string."""
    if not is_configured():
        return False, "NATLAS_BASE_URL is not set"
    try:
        with urllib.request.urlopen(endpoint("/health"), timeout=timeout) as resp:
            return True, json.load(resp)
    except urllib.error.HTTPError as exc:  # 503 = gateway up, an upstream (LLM/ASR) down
        try:
            return False, json.load(exc)
        except Exception:
            return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, str(exc) or exc.__class__.__name__


def compose(language, facts, guidance, question=None, history=None):
    """Ask N-ATLaS to write a grounded, personal message in the user's language."""
    system = SYSTEM_PROMPT.format(language=LANGUAGE_NAMES.get(language, "English"))
    context = "FACTS:\n" + "\n".join(f"- {f}" for f in facts)
    if guidance:
        context += "\n\nGUIDANCE (WHO/NPHCDA):\n" + "\n".join(f"- {g}" for g in guidance)
    messages = [{"role": "system", "content": system + "\n\n" + context}]
    for role, content in (history or [])[-6:]:
        messages.append({"role": role, "content": content})
    messages.append(
        {"role": "user", "content": question or "Write a short personal health alert from these facts."}
    )
    return chat(messages, language=language)
