"""Spoken replies: the answer is read aloud in the user's language by the N-ATLaS gateway's voices.

The gateway returns WAV; WhatsApp only accepts compressed audio, so clips are stored as MP3
(lameenc). Without lameenc the WAV is kept, which browsers can still play.
"""

import io
import logging
import re
import wave

from . import natlas
from .models import VoiceClip

log = logging.getLogger(__name__)

MAX_CHARS = 780  # the gateway accepts up to 800
URL = re.compile(r"https?://\S+")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def speakable(text):
    """Drop links, emoji and markdown, and cut at a sentence end so the clip doesn't stop mid-word."""
    text = URL.sub("", text)
    text = EMOJI.sub("", text)
    text = re.sub(r"[*_#>`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= MAX_CHARS:
        return text
    cut = text[:MAX_CHARS]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > MAX_CHARS // 3 else cut.rsplit(" ", 1)[0]


def wav_to_mp3(wav_bytes):
    """Return MP3 bytes, or None if lameenc is unavailable or the WAV is not 16-bit PCM."""
    try:
        import lameenc
    except ImportError:
        return None
    with wave.open(io.BytesIO(wav_bytes)) as w:
        if w.getsampwidth() != 2:
            return None
        rate, channels, pcm = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    enc = lameenc.Encoder()
    enc.set_bit_rate(32)
    enc.set_in_sample_rate(rate)
    enc.set_channels(channels)
    enc.set_quality(5)
    return bytes(enc.encode(pcm) + enc.flush())


def make_clip(text, language, message=None):
    """Render and store a spoken reply. Returns a VoiceClip, or None if speech is unavailable."""
    if message is not None:
        existing = message.voice_clips.first()
        if existing:
            return existing
    spoken = speakable(text)
    result = natlas.speak(spoken, language)
    if not result:
        return None
    wav, voice = result
    try:
        mp3 = wav_to_mp3(wav)
    except Exception as exc:  # malformed WAV: keep the original
        log.warning("MP3 conversion failed: %s", exc)
        mp3 = None
    return VoiceClip.objects.create(
        message=message, language=language, voice=voice[:80],
        audio=mp3 or wav, content_type="audio/mpeg" if mp3 else "audio/wav",
    )
