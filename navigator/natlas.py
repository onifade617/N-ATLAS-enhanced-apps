"""Lafiya's N-ATLaS integration, built on the natlas-health SDK (``natlas_health``).

Lafiya is the reference application for the kit: this module only adapts Django settings to a
``NatlasClient`` and keeps Lafiya's contract that a failed call returns ``None`` (the product then falls
back to its grounded templates / browser speech, so it never breaks during a cold start).

Configure with NATLAS_BASE_URL (or NATLAS_API_URL), NATLAS_API_KEY, NATLAS_MODEL and NATLAS_TIMEOUT.
"""

import logging

from django.conf import settings

from natlas_health import HealthAssistant, NatlasClient, NatlasError

log = logging.getLogger(__name__)


def client():
    """A client for the current settings (built per call so override_settings in tests takes effect)."""
    cfg = settings.NATLAS
    return NatlasClient(base_url=cfg["API_URL"], api_key=cfg["API_KEY"], model=cfg["MODEL"], timeout=cfg["TIMEOUT"])


def is_configured():
    return bool(settings.NATLAS["API_URL"])


def endpoint(path):
    return client().url(path)


def chat(messages, language=None, temperature=0.3, max_tokens=500):
    """Send chat messages to N-ATLaS. Returns the reply text or None on failure."""
    if not is_configured():
        return None
    try:
        return client().chat(messages, language=language, temperature=temperature, max_tokens=max_tokens).text or None
    except NatlasError as exc:
        log.warning("N-ATLaS chat failed: %s", exc)
        return None


def transcribe(audio_bytes, filename, content_type, language):
    """Speech-to-text through the gateway's per-language Whisper models. Returns text or None."""
    if not is_configured() or not audio_bytes:
        return None
    try:
        return client().transcribe(audio_bytes, filename, content_type, language).text or None
    except NatlasError as exc:
        log.warning("N-ATLaS transcription failed: %s", exc)
        return None


def speak(text, language):
    """Text-to-speech via the gateway's MMS-TTS voices. Returns (wav_bytes, voice_name) or None."""
    if not is_configured() or not text:
        return None
    try:
        speech = client().speak(text, language)
        return speech.audio, speech.voice
    except NatlasError as exc:  # FeatureNotEnabledError = speech not enabled on this gateway
        log.warning("N-ATLaS speech failed: %s", exc)
        return None


def health(timeout=10):
    """GET /health (no key needed). Returns (ok, details)."""
    status = client().health(timeout=timeout)
    return status.ok, status.details


def compose(language, facts, guidance, question=None, history=None):
    """Ask N-ATLaS to write a grounded, personal message in the user's language (None if unavailable)."""
    if not is_configured():
        return None
    return HealthAssistant(client()).compose(language, facts, guidance, question=question, history=history)
