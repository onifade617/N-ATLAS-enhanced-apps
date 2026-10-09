"""Danger-sign detection that never depends on the model.

If a message mentions a danger sign (bleeding in pregnancy, convulsions, fast breathing...), an app must
tell the person to get care now, whatever N-ATLaS replies. ``detect_danger`` is a transparent multilingual
keyword matcher you can extend; ``EMERGENCY_NOTICE`` is the fixed text to put before the model's answer.

Keyword rules: matching is case- and accent-insensitive on whole words; a trailing "*" matches a prefix.
Hausa, Yoruba, Igbo and Pidgin keywords are draft lists and need native-speaker review before a pilot.
"""

import re
import unicodedata

DANGER_KEYWORDS = [
    # English (WHO/UNICEF IMCI and pregnancy danger signs)
    "bleeding", "bleed*", "convuls*", "fits", "seizure*", "unconscious", "fainted", "fainting",
    "not breathing", "difficulty breathing", "breathing fast", "fast breathing", "chest indrawing",
    "severe headache", "blurred vision", "swollen face", "swelling of face", "water broke", "waters broke",
    "baby not moving", "not moving", "not feeding", "cannot feed", "unable to drink", "cannot drink",
    "stiff neck", "severe abdominal pain", "severe pain",
    # Pidgin
    "blood dey comma", "blood dey come", "dey shake", "no dey breathe", "pikin no dey move",
    # Yoruba
    "eje n jade", "eje jade", "eje n da", "giri", "daku",
    # Hausa
    "zubar jini", "jini na fita", "farfadiya", "suma", "ba ya numfashi",
    # Igbo
    "obara na-agba", "obara na agba", "obara na-asa",
]

# Shown before the model's answer whenever a danger sign is detected.
EMERGENCY_NOTICE = {
    "en": "This may be a danger sign. Go to the nearest health facility NOW or call 112.",
    "pcm": "This fit be danger sign. Go the nearest hospital NOW or call 112.",
    "yo": "Èyí lè jẹ́ àmì ewu. Ẹ lọ sí ilé ìwòsàn tó súnmọ́ jùlọ NÍ BÁYÌÍ tàbí kí ẹ pe 112.",
    "ha": "Wannan na iya zama alamar hadari. Ku je asibiti mafi kusa YANZU ko ku kira 112.",
    "ig": "Nke a nwere ike ịbụ ihe ịrịba ama dị ize ndụ. Gaa n'ụlọ ọgwụ kacha nso UGBU A ma ọ bụ kpọọ 112.",
}


def normalize(text):
    """Lower-case, straighten apostrophes, strip accents/tone marks, collapse whitespace ("Ẹ̀jẹ̀" -> "eje")."""
    text = (text or "").lower().replace("’", "'").replace("‘", "'").replace("ʼ", "'")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def _kw_regex(kw):
    if kw.endswith("*"):
        return r"\b" + re.escape(kw[:-1])
    return r"\b" + re.escape(kw) + r"\b"


def matches(norm_text, keywords):
    """True if any keyword occurs in already-normalized text."""
    return any(re.search(_kw_regex(normalize(k)), norm_text) for k in keywords)


def detect_danger(text, extra_keywords=()):
    """True if ``text`` mentions a danger sign. Pass your own ``extra_keywords`` to extend the list."""
    return matches(normalize(text), list(DANGER_KEYWORDS) + list(extra_keywords))


def emergency_notice(language):
    return EMERGENCY_NOTICE.get(language, EMERGENCY_NOTICE["en"])
