"""Text helpers for replies that are sent on WhatsApp and read aloud."""

import re

MAX_SPEECH_CHARS = 780  # the gateway's /v1/audio/speech accepts up to 800
URL = re.compile(r"https?://\S+")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")
MARKDOWN = re.compile(r"(\*\*|__|^#{1,6}\s|^\s*[-*•]\s|^\s*\d+[.)]\s|`)", re.MULTILINE)
SENTENCE_END = re.compile(r"[.!?։።](?:\s|$)")


def has_markdown(text):
    return bool(MARKDOWN.search(text or ""))


def plain_text(text):
    """Remove markdown emphasis, headings and list markers but keep the words."""
    text = re.sub(r"^#{1,6}\s*", "", text or "", flags=re.MULTILINE)
    text = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|__|`)", "", text)
    return text.strip()


def sentence_count(text):
    text = (text or "").strip()
    if not text:
        return 0
    return len(SENTENCE_END.findall(text)) + (0 if SENTENCE_END.search(text[-1] + " ") else 1)


def speakable(text, max_chars=MAX_SPEECH_CHARS):
    """Drop links, emoji and markdown, and cut at a sentence end so a spoken clip doesn't stop mid-word."""
    text = URL.sub("", text or "")
    text = EMOJI.sub("", text)
    text = re.sub(r"[*_#>`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > max_chars // 3 else cut.rsplit(" ", 1)[0]
