"""Languages N-ATLaS serves, and how each maps onto the gateway's chat template and ASR models."""

LANGUAGES = {
    "en": "English",
    "ha": "Hausa",
    "yo": "Yoruba",
    "ig": "Igbo",
    "pcm": "Nigerian Pidgin",
}

# Codes the gateway's chat template understands. Anything else (e.g. Pidgin) is sent without "language".
CHAT_LANGUAGES = {"en", "ha", "ig", "yo"}

# Per-language Whisper models behind POST /v1/audio/transcriptions. Pidgin has no dedicated
# ASR model, so it is transcribed with the Nigerian-accented English model.
ASR_LANGUAGE = {"en": "en", "ha": "ha", "ig": "ig", "yo": "yo", "pcm": "en"}

# MMS-TTS voices behind POST /v1/audio/speech. Pidgin is read with the English voice.
TTS_LANGUAGE = {"en": "en", "ha": "ha", "ig": "ig", "yo": "yo", "pcm": "en"}


def language_name(code):
    return LANGUAGES.get(code, "English")


def chat_language(code):
    """The value to send as "language" on /v1/chat/completions, or None to leave it out."""
    return code if code in CHAT_LANGUAGES else None


def asr_language(code):
    return ASR_LANGUAGE.get(code, "en")


def tts_language(code):
    return TTS_LANGUAGE.get(code, "en")
