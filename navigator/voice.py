"""Spoken replies: the answer is read aloud in the user's language by the N-ATLaS gateway's voices.

The gateway returns WAV; WhatsApp only accepts compressed audio, so clips are stored as MP3
(lameenc). Without lameenc the WAV is kept, which browsers can still play.
Text cleanup and MP3 conversion come from the natlas-health SDK.
"""

import logging

from natlas_health.audio import wav_to_mp3
from natlas_health.text import speakable

from . import natlas
from .models import VoiceClip

log = logging.getLogger(__name__)

__all__ = ["make_clip", "speakable", "wav_to_mp3"]


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
