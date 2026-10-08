"""WhatsApp voice-note channel (Twilio).

Inbound flow: a family member sends a voice note or text on WhatsApp →
Twilio calls /whatsapp/twilio/ → the voice note is transcribed by the official
N-ATLaS ASR (gateway) → the Care Navigator answers (N-ATLaS) → the reply, nearest
facility and any booked reminder go back on WhatsApp via Twilio's REST API.

First contact runs a short onboarding: language → consent (NDPA 2023) → LGA/location.
"""

import base64
import difflib
import hashlib
import hmac
import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from core.geo import haversine_km
from core.models import LGA, Profile

from . import natlas
from .engine import ask, normalize
from .models import Conversation, Message, WhatsAppContact
from .phrases import phrase
from .voice import make_clip
from .whatsapp_texts import (LANGUAGE_CHOICES, LANGUAGE_MENU, LANGUAGE_WORDS, MENU_WORDS, NO_WORDS, SKIP_WORDS,
                             STOP_WORDS, YES_WORDS, text)

log = logging.getLogger(__name__)

OUTBOX = []  # messages "sent" when Twilio is not configured (dev/tests)
MAX_BODY = 1500  # Twilio WhatsApp limit is 1600 characters per message
TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


# ------------------------------------------------------------------ Twilio I/O


def is_configured():
    return bool(settings.TWILIO["ACCOUNT_SID"] and settings.TWILIO["AUTH_TOKEN"])


def signature_valid(url, params, signature):
    """Twilio request validation: HMAC-SHA1(auth_token, url + sorted(key+value...)), base64."""
    token = settings.TWILIO["AUTH_TOKEN"]
    payload = url + "".join(k + v for k in sorted(params) for v in params.getlist(k))
    expected = base64.b64encode(hmac.new(token.encode(), payload.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(expected, signature or "")


def _basic_auth():
    raw = f"{settings.TWILIO['ACCOUNT_SID']}:{settings.TWILIO['AUTH_TOKEN']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Twilio media URLs redirect to a pre-signed CDN URL that rejects our Basic auth header."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlparse(newurl).hostname != urllib.parse.urlparse(req.full_url).hostname:
            new.remove_header("Authorization")
        return new


def download_media(url):
    req = urllib.request.Request(url, headers={"Authorization": _basic_auth()} if is_configured() else {})
    opener = urllib.request.build_opener(_StripAuthOnRedirect)
    with opener.open(req, timeout=30) as resp:
        data = resp.read(settings.MAX_VOICE_UPLOAD_BYTES + 1)
    if len(data) > settings.MAX_VOICE_UPLOAD_BYTES:
        raise ValueError("voice note too large")
    return data


def _chunks(body):
    while len(body) > MAX_BODY:
        cut = body.rfind("\n", 0, MAX_BODY)
        cut = cut if cut > MAX_BODY // 2 else MAX_BODY
        yield body[:cut]
        body = body[cut:].lstrip()
    if body:
        yield body


def send(phone, body, media_url=None):
    """Send text (split into WhatsApp-sized chunks) or, with media_url, one audio/media message."""
    chunks = list(_chunks(body)) if body else [""]
    for chunk in chunks:
        if not is_configured():
            log.info("WhatsApp (not sent, Twilio unconfigured) to %s: %s %s", phone, chunk[:80], media_url or "")
            OUTBOX.append((phone, chunk) if not media_url else (phone, chunk, media_url))
            continue
        fields = {"From": settings.TWILIO["WHATSAPP_FROM"], "To": f"whatsapp:{phone}"}
        if chunk:
            fields["Body"] = chunk
        if media_url:
            fields["MediaUrl"] = media_url
        data = urllib.parse.urlencode(fields).encode()
        req = urllib.request.Request(
            TWILIO_API.format(sid=settings.TWILIO["ACCOUNT_SID"]), data=data, method="POST",
            headers={"Authorization": _basic_auth(), "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                json.load(resp)
        except Exception as exc:
            log.error("Twilio send to %s failed: %s", phone, exc)


# ------------------------------------------------------------------ helpers


def e164(raw):
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0") and len(digits) == 11:  # local Nigerian format 080...
        digits = "234" + digits[1:]
    return "+" + digits if digits else ""


def find_profile_by_phone(phone):
    """Link a WhatsApp number to an existing (e.g. CHW-enrolled) household, never to demo data."""
    target = phone.lstrip("+")
    for p in Profile.objects.filter(is_demo=False, consent_given=True).exclude(phone=""):
        if e164(p.phone).lstrip("+") == target:
            return p
    return None


def nearest_lga(lat, lon):
    return min(LGA.objects.all(), key=lambda l: haversine_km(lat, lon, l.latitude, l.longitude), default=None)


def _words(value):
    return re.sub(r"[^a-z0-9]+", " ", normalize(value)).strip()


def match_lga(said):
    """Find the LGA named in free text ("I live in Surulere, Lagos"). Returns None if unknown or ambiguous.

    774 LGAs share some names across states (e.g. Surulere in Lagos and Oyo), so a mentioned
    state is used to disambiguate; otherwise the person is asked again.
    """
    text_ = f" {_words(said)} "
    if not text_.strip():
        return None
    lgas = list(LGA.objects.select_related("state"))
    hits = [l for l in lgas if f" {_words(l.name)} " in text_]
    if not hits:
        names = {}
        for l in lgas:
            names.setdefault(_words(l.name), []).append(l)
        close = difflib.get_close_matches(text_.strip(), names, n=1, cutoff=0.8)
        hits = names[close[0]] if close else []
    if not hits:
        return None
    in_state = [l for l in hits if f" {_words(l.state.name)} " in text_ and _words(l.state.name) != _words(l.name)]
    hits = in_state or hits
    longest = max(len(l.name) for l in hits)
    hits = [l for l in hits if len(l.name) == longest]  # "Ibadan North East" beats "Ibadan North"
    return hits[0] if len(hits) == 1 else None


def format_reply(result, transcript=None, language="en"):
    parts = []
    if transcript:
        parts.append(f"_{text(language, 'you_said')}: \"{transcript}\"_")
    parts.append(result["reply"])
    if result.get("facilities"):
        f = result["facilities"][0]
        keys = ("open_now", "closed_now") if f.get("hours_verified", True) else ("usually_open", "usually_closed")
        status = phrase(language, keys[0]) if f["open_now"] else phrase(language, keys[1], hours=f.get("hours_text", f["hours"]))
        line = f"📍 *{f['name']}* — {f['distance_km']} km. {status}"
        if f.get("phone"):
            line += f"\n📞 {f['phone']}"
        parts.append(line + f"\n🗺️ {f['map_url']}")
    if result.get("reminder"):
        parts.append(f"🔔 {result['reminder']['title']}")
    return "\n\n".join(parts)


def _recent_conversation(profile):
    since = timezone.now() - timedelta(hours=24)
    return profile.conversations.filter(channel="whatsapp", messages__created_at__gte=since).distinct().first()


def _erase(contact):
    profile = contact.profile
    contact.delete()
    if profile:
        user = profile.user
        profile.delete()
        if user:
            user.delete()


# ------------------------------------------------------------------ main handler


@transaction.atomic
def _onboard(contact, cmd, body, data):
    """Handle the onboarding states. Returns a reply string, or None when the contact is ready."""
    lang = contact.language
    if contact.state == "language":
        choice = LANGUAGE_CHOICES.get(cmd)
        if not choice:
            return LANGUAGE_MENU
        contact.language = choice
        if contact.profile:
            contact.profile.language = choice
            contact.profile.save(update_fields=["language"])
            contact.state = "ready"
            contact.save()
            return text(choice, "menu")
        contact.state = "consent"
        contact.save()
        return text(choice, "consent")

    if contact.state == "consent":
        if cmd in YES_WORDS:
            contact.profile = Profile.objects.create(
                full_name=contact.display_name or "WhatsApp user", phone=contact.phone, language=lang,
                consent_given=True, consent_at=timezone.now(),
            )
            contact.state = "location"
            contact.save()
            return text(lang, "location")
        if cmd in NO_WORDS:
            contact.delete()
            return text(lang, "consent_declined")
        return text(lang, "consent")

    if contact.state == "location":
        if cmd in SKIP_WORDS:
            contact.state = "ready"
            contact.save()
            return text(lang, "menu")
        lga = _location_from(contact, body, data)
        if lga is None:
            return text(lang, "location_unknown")
        contact.state = "ready"
        contact.save()
        return text(lang, "location_saved", lga=lga)
    return None


def _location_from(contact, body, data):
    """Set the profile's LGA from a shared WhatsApp location, typed text or a voice note."""
    profile = contact.profile
    lat, lon = data.get("Latitude"), data.get("Longitude")
    if lat and lon:
        profile.latitude, profile.longitude = float(lat), float(lon)
        profile.lga = nearest_lga(profile.latitude, profile.longitude)
    else:
        said = body or _transcribe_voice(contact, data) or ""
        profile.lga = match_lga(said)
    profile.save(update_fields=["latitude", "longitude", "lga"])
    return profile.lga


def _transcribe_voice(contact, data):
    if int(data.get("NumMedia") or 0) < 1 or not (data.get("MediaContentType0") or "").startswith("audio"):
        return None
    try:
        audio = download_media(data["MediaUrl0"])
    except Exception as exc:
        log.warning("Could not download WhatsApp voice note: %s", exc)
        return None
    ext = (data.get("MediaContentType0") or "audio/ogg").split("/")[-1].split(";")[0]
    return natlas.transcribe(audio, f"voice.{ext}", data.get("MediaContentType0"), contact.language)


def handle_inbound(data):
    """Process one inbound Twilio WhatsApp message (a dict of Twilio form fields)."""
    phone = e164((data.get("From") or "").replace("whatsapp:", ""))
    if not phone:
        return
    body = (data.get("Body") or "").strip()
    cmd = normalize(body)

    contact = WhatsAppContact.objects.filter(phone=phone).select_related("profile").first()
    if cmd in STOP_WORDS:
        lang = contact.language if contact else "en"
        if contact:
            _erase(contact)
        send(phone, text(lang, "stopped"))
        return

    if contact is None:
        contact = WhatsAppContact.objects.create(phone=phone, display_name=(data.get("ProfileName") or "")[:80])
        existing = find_profile_by_phone(phone)
        if existing and not hasattr(existing, "whatsapp"):
            contact.profile = existing  # enrolled by a CHW: consent already recorded
            contact.language = existing.language
            contact.state = "ready"
            contact.save()
            send(phone, text(contact.language, "menu"))
            if cmd in MENU_WORDS or not (body or data.get("NumMedia")):
                return
        else:
            send(phone, LANGUAGE_MENU)
            return
    else:
        contact.save(update_fields=["updated_at"])  # marks the 24 h WhatsApp session as active

    if cmd in LANGUAGE_WORDS:
        contact.state = "language"
        contact.save()
        send(phone, LANGUAGE_MENU)
        return

    if contact.state != "ready":
        reply = _onboard(contact, cmd, body, data)
        if reply:
            send(phone, reply)
        return

    profile = contact.profile
    lang = contact.language
    if data.get("Latitude") and data.get("Longitude"):
        send(phone, text(lang, "location_saved", lga=_location_from(contact, "", data)))
        return

    question, input_mode, asr = body, "text", ""
    if int(data.get("NumMedia") or 0) > 0 and (data.get("MediaContentType0") or "").startswith("audio"):
        question = _transcribe_voice(contact, data)
        input_mode, asr = "voice", "n-atlas"
        if not question:
            send(phone, text(lang, "voice_failed"))
            return
    if not question or cmd in MENU_WORDS:
        send(phone, text(lang, "menu"))
        return

    result = ask(profile, question[:1000], language=lang, conversation=_recent_conversation(profile),
                 channel="whatsapp", input_mode=input_mode, asr_engine=asr)
    send(phone, format_reply(result, transcript=question if input_mode == "voice" else None, language=lang))
    if input_mode == "voice":
        send_voice_reply(phone, result, lang)


def send_voice_reply(phone, result, language):
    """Voice in, voice out: read the answer aloud in the same language (gateway MMS-TTS voices)."""
    if not (settings.SPOKEN_REPLIES and settings.PUBLIC_BASE_URL):
        return False  # Twilio must be able to fetch the audio from a public URL
    message = Message.objects.filter(pk=result.get("message_id")).first()
    clip = make_clip(result["reply"], language, message)
    if clip is None or clip.content_type != "audio/mpeg":  # WhatsApp rejects WAV
        return False
    url = settings.PUBLIC_BASE_URL.rstrip("/") + reverse("voice_file", args=[clip.id, clip.extension])
    send(phone, "", media_url=url)
    return True


def deliver_alert(alert):
    """Push a new personalised alert to WhatsApp if the person has an active (24 h) session."""
    contact = getattr(alert.profile, "whatsapp", None)
    if not contact or contact.state != "ready" or contact.updated_at < timezone.now() - timedelta(hours=24):
        return False
    msg = f"*{alert.title}*\n\n{alert.message}"
    if alert.reason:
        msg += f"\n\nℹ️ {alert.reason}"
    send(contact.phone, msg)
    alert.channel = "whatsapp"
    alert.save(update_fields=["channel"])
    return True
