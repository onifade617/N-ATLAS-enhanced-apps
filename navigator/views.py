import json
import logging
import threading

from django.conf import settings
from django.db import connection
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.decorators import profile_required
from core.models import LANGUAGE_NAMES, Facility

from . import natlas, voice, whatsapp
from .engine import ask

log = logging.getLogger(__name__)
from .models import Message, Referral, VoiceClip

SUGGESTIONS = {
    "en": ["Which vaccine does my baby need next?", "Where is the nearest clinic?", "Is malaria risk high this week?",
           "My child has fever", "How can I control my blood pressure?"],
    "yo": ["Abẹ́rẹ́ àjẹsára wo ni ọmọ mi nílò báyìí?", "Níbo ni ilé ìwòsàn tó súnmọ́ jùlọ wà?", "Ṣé ewu ibà ga ní ọ̀sẹ̀ yìí?"],
    "ha": ["Wace allurar rigakafi ce ta gaba ga jaririna?", "Ina asibiti mafi kusa?", "Akwai hadarin zazzabin cizon sauro a wannan makon?"],
    "ig": ["Kedu ọgwụ mgbochi nwa m chọrọ ọzọ?", "Ebee ka ụlọ ọgwụ kacha nso dị?", "Ịba ọ dị elu n'izu a?"],
    "pcm": ["Which vaccine my pikin need next?", "Where the nearest clinic dey?", "Malaria risk dey high this week?"],
}


@profile_required
def chat(request, profile):
    conv = profile.conversations.first()
    history = list(conv.messages.all()) if conv else []
    return render(
        request,
        "navigator/chat.html",
        {
            "conversation": conv,
            "history": history,
            "suggestions": SUGGESTIONS,
            "language_names": LANGUAGE_NAMES,
        },
    )


@require_POST
@profile_required
def api_ask(request, profile):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    text = (body.get("text") or "").strip()
    if not text:
        return JsonResponse({"error": "Please type or say a question."}, status=400)
    language = body.get("language") if body.get("language") in LANGUAGE_NAMES else profile.language
    input_mode = "voice" if body.get("input_mode") == "voice" else "text"
    asr = body.get("asr") if body.get("asr") in ("n-atlas", "browser") else ""
    result = ask(profile, text[:1000], language=language, conversation_id=body.get("conversation_id"),
                 channel="web", input_mode=input_mode, asr_engine=asr)
    return JsonResponse(result)


@require_POST
@profile_required
def api_transcribe(request, profile):
    """Voice note -> text via the N-ATLaS gateway's Hausa/Igbo/Yoruba/English ASR models."""
    if not natlas.is_configured():
        return JsonResponse({"error": "Server speech recognition is not configured."}, status=503)
    audio = request.FILES.get("audio")
    if audio is None:
        return JsonResponse({"error": "No audio received."}, status=400)
    if audio.size > settings.MAX_VOICE_UPLOAD_BYTES:
        return JsonResponse({"error": "Recording is too long. Please keep it under a minute."}, status=413)
    language = request.POST.get("language") if request.POST.get("language") in LANGUAGE_NAMES else profile.language
    text = natlas.transcribe(audio.read(), audio.name or "voice.webm", audio.content_type, language)
    if not text:
        return JsonResponse(
            {"error": "Lafiya could not hear that clearly (the speech service may be starting up). Please try again or type."},
            status=502,
        )
    return JsonResponse({"text": text, "language": language})


@csrf_exempt
@require_POST
def twilio_whatsapp(request):
    """Twilio WhatsApp webhook. Replies are sent via the REST API, so we answer Twilio immediately."""
    if settings.TWILIO["VALIDATE_SIGNATURE"] and settings.TWILIO["AUTH_TOKEN"]:
        url = (settings.PUBLIC_BASE_URL.rstrip("/") + request.get_full_path()) if settings.PUBLIC_BASE_URL \
            else request.build_absolute_uri()
        if not whatsapp.signature_valid(url, request.POST, request.headers.get("X-Twilio-Signature")):
            return HttpResponseForbidden("Invalid Twilio signature")
    data = request.POST.dict()

    def process():
        try:
            whatsapp.handle_inbound(data)
        except Exception:
            log.exception("WhatsApp message failed")
        finally:
            if settings.WHATSAPP_ASYNC:
                connection.close()

    if settings.WHATSAPP_ASYNC:
        threading.Thread(target=process, daemon=True).start()
    else:
        process()
    return HttpResponse("<Response></Response>", content_type="text/xml")


@require_POST
@profile_required
def api_speak(request, profile):
    """Spoken version of one of this user's answers, in the answer's language (N-ATLaS gateway voices)."""
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        body = {}
    message = get_object_or_404(Message, pk=body.get("message_id"), role="assistant", conversation__profile=profile)
    clip = voice.make_clip(message.text, message.language, message) if settings.SPOKEN_REPLIES else None
    if clip is None:
        return JsonResponse({"error": "Spoken replies are not available right now."}, status=503)
    return JsonResponse({"url": reverse("voice_file", args=[clip.id, clip.extension]), "voice": clip.voice})


def voice_file(request, clip_id, ext):
    """Public, unguessable URL (UUID) so Twilio can fetch voice replies for WhatsApp."""
    clip = get_object_or_404(VoiceClip, pk=clip_id)
    if ext != clip.extension:
        raise Http404
    resp = HttpResponse(bytes(clip.audio), content_type=clip.content_type)
    resp["Cache-Control"] = "private, max-age=86400"
    return resp


@require_POST
@profile_required
def accept_referral(request, profile):
    """User chooses to go to a facility: record an accepted referral (Act step)."""
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        body = {}
    facility = get_object_or_404(Facility, pk=body.get("facility_id"))
    ref = None
    if body.get("referral_id"):
        ref = Referral.objects.filter(pk=body["referral_id"], profile=profile).first()
    if ref:
        ref.facility = facility
        ref.status = "accepted"
        ref.save(update_fields=["facility", "status"])
    else:
        ref = Referral.objects.create(
            profile=profile, facility=facility, reason=body.get("reason", "Care Navigator referral")[:200],
            status="accepted",
        )
    return JsonResponse({"ok": True, "referral_id": ref.id, "facility": facility.name})
