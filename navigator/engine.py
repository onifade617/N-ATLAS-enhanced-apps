"""Care Navigator: grounded, multilingual health guidance and symptom-to-service referral.

Flow for each question:
 1. Safety first — detect danger signs and always give emergency referral.
 2. Detect the intent (multilingual keywords).
 3. Gather grounded FACTS from the person's own records (children, pregnancy,
    LGA climate risk, nearest facilities) plus GUIDANCE from the knowledge base.
 4. N-ATLAS writes the reply in the user's language; if it is unavailable the
    localized template engine composes it from the same facts.
 5. Act: book reminders, suggest referrals, return facilities for the map.
"""

import time
from datetime import date, timedelta

from alerts.models import Alert
from climateguard.models import LEVEL_ORDER
from climateguard.risk import latest_risks
from core.geo import facility_payload, nearest_facilities
from core.models import SERVICE_NAMES
from immunitrack.services import next_due
from mamacare.models import DangerSign, Milestone

from natlas_health.safety import DANGER_KEYWORDS, matches, normalize

from . import natlas
from .knowledge import SOURCES, SYMPTOMS, TOPICS
from .models import Conversation, Message, Referral
from .phrases import phrase

INTENTS = [
    ("vaccine", ["vaccin*", "immuni*", "injection*", "jab*", "ajesara", "abere", "rigakafi", "allura*", "mgbochi"]),
    ("clinic", ["clinic*", "hospital*", "facility", "facilities", "health cent*", "phc", "nearest", "near me",
                "ile iwosan", "asibiti", "ulo ogwu", "where i fit"]),
    ("fever", ["fever*", "hot body", "body hot", "body dey hot", "temperature", "ara gbona", "ara n gbona",
               "zazzabi", "ahu oku", "ahu na-ekpo oku"]),
    ("pregnancy", ["pregnan*", "antenatal", "anc", "belle", "oyun", "ciki", "ime", "due date", "expecting"]),
    ("malaria", ["malaria", "mosquito*", "net", "iba", "sauro", "anwunta", "efon"]),
    ("heat", ["heat*", "hot weather", "too hot", "sun too", "ooru", "zafi", "okpomoku"]),
    ("flood", ["flood*", "ambaliya", "akunya omi", "iju mmiri", "heavy rain"]),
    ("hypertension", ["blood pressure", "bp", "hypertens*", "hawan jini", "eje riru", "obara mgbali", "high blood"]),
    ("headache", ["headache", "head dey pain", "ciwon kai", "ori fifo", "isi owuwa"]),
    ("diabetes", ["diabet*", "sugar", "suga", "shuga", "ciwon suga", "atogbe"]),
    ("diarrhoea", ["diarrh*", "running stomach", "stooling", "gudawa", "igbe gburu", "otita", "cholera"]),
    ("cough", ["cough*", "ikọ", "iko", "tari", "ukwara"]),
    ("nutrition", ["food", "eat*", "nutrition", "breastfe*", "breast milk", "feeding", "abinci", "ounje", "nri",
                   "shayarwa", "oyan", "complementary"]),
    ("hygiene", ["wash hand*", "hygiene", "clean water", "soap"]),
    ("milestones", ["milestone*", "walk*", "talk*", "crawl*", "sit up", "develop*", "growth"]),
    ("danger_signs", ["danger sign*", "warning sign*"]),
    ("thanks", ["thank*", "nagode", "ese", "dalu", "imeela", "e se"]),
    ("greeting", ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "sannu", "bawo",
                  "kedu", "how far", "ndewo", "e kaaro", "ekaaro", "barka"]),
]

CLINIC_SERVICE_KEYWORDS = {
    "emergency": ["emergency", "urgent"],
    "immunization": ["vaccin*", "immuni*", "ajesara", "rigakafi"],
    "antenatal": ["antenatal", "anc", "pregnan*", "belle", "oyun", "ciki"],
    "delivery": ["deliver*", "labour", "labor", "give birth", "born"],
    "malaria": ["malaria", "fever", "test"],
    "ncd": ["bp", "blood pressure", "diabet*", "sugar"],
}

SERVICE_FOR_INTENT = {
    "vaccine": "immunization",
    "clinic": None,
    "fever": "malaria",
    "pregnancy": "antenatal",
    "malaria": "malaria",
    "heat": "ncd",
    "flood": "emergency",
    "hypertension": "ncd",
    "headache": "ncd",
    "diabetes": "ncd",
    "diarrhoea": "nutrition",
    "cough": "nutrition",
    "nutrition": "nutrition",
    "hygiene": None,
    "milestones": "nutrition",
}

TOPIC_FOR_INTENT = {
    "hypertension": "hypertension",
    "headache": "hypertension",
    "diabetes": "diabetes",
    "nutrition": "nutrition",
    "diarrhoea": "hygiene",
    "hygiene": "hygiene",
    "malaria": "malaria",
    "fever": "malaria",
    "heat": "heat",
    "flood": "flood",
    "pregnancy": "pregnancy",
    "milestones": "milestones",
}

TOPIC_ONLY_INTENTS = {
    "hypertension", "headache", "diabetes", "nutrition", "hygiene", "diarrhoea", "milestones", "danger_signs",
}

SYMPTOM_FOR_INTENT = {"fever": "fever", "diarrhoea": "diarrhoea", "cough": "cough", "headache": "headache"}


def detect_danger(norm_text):
    """The SDK's multilingual danger signs plus any keywords health workers add in the admin."""
    keywords = list(DANGER_KEYWORDS)
    for ds in DangerSign.objects.exclude(keywords=""):
        keywords.extend(k.strip() for k in ds.keywords.split(",") if k.strip())
    return matches(norm_text, keywords)


def detect_intent(norm_text):
    for intent, keywords in INTENTS:
        if matches(norm_text, keywords):
            return intent
    return "fallback"


def _fmt(d):
    return d.strftime("%d %b %Y")


def _pick_child(profile, norm_text, today):
    children = [c for c in profile.children.all() if c.is_under_five]
    if not children:
        return None
    for c in children:
        if normalize(c.name) in norm_text:
            return c
    pending = [(next_due(c, today), c) for c in children]
    pending = [(nd, c) for nd, c in pending if nd]
    if pending:
        return min(pending, key=lambda x: x[0]["due_date"])[1]
    return children[-1]


class Reply:
    def __init__(self, profile, language):
        self.profile = profile
        self.language = language
        self.parts = []  # localized template sentences
        self.facts = []  # facts for N-ATLAS grounding
        self.guidance = []
        self.facilities = []
        self.reminder = None
        self.referral = None
        self.risk = None
        self.sources = set()
        self.emergency = False
        self.topic = None

    def say(self, key, **ctx):
        self.parts.append(phrase(self.language, key, **ctx))


def _add_facilities(reply, service, limit=3, reason=None, urgency=None):
    origin = reply.profile.location()
    found = nearest_facilities(origin, service=service, limit=limit)
    if not found:
        return None
    reply.facilities = [facility_payload(f, d) for f, d in found]
    # Prefer an open facility close to the nearest one.
    best = next(((f, d) for f, d in found if f.open_now and d <= found[0][1] + 5), found[0])
    f, d = best
    label = SERVICE_NAMES.get(service, "care") if service else "care"
    status = ("open now" if f.open_now else "closed now") if f.hours_verified else (
        ("usually open at this time" if f.open_now else "usually closed at this time") + " - hours not confirmed")
    reply.facts.append(
        f"Nearest facility for {label}: {f.name} ({f.get_facility_type_display()}, {f.ownership or 'ownership unknown'}), "
        f"{d} km away, {status} ({f.hours_text}), phone {f.phone or 'not listed'}."
    )
    if service:
        reply.say("nearest", service=label.lower(), facility=f.name, distance=d)
    else:
        reply.say("nearest_any", facility=f.name, distance=d)
    if f.hours_verified:
        reply.say("open_now" if f.open_now else "closed_now", hours=f.hours_text)
    else:
        reply.say("usually_open" if f.open_now else "usually_closed", hours=f.hours_text)
    if reason:
        reply.referral = Referral.objects.create(
            profile=reply.profile, facility=f, service=service or "", reason=reason, urgency=urgency or "routine"
        )
    return f


def _add_risk(reply, hazard, always=False):
    lga = reply.profile.lga
    if not lga:
        return
    risk = latest_risks(lga).get(hazard)
    if not risk:
        return
    elevated = LEVEL_ORDER[risk.level] >= LEVEL_ORDER["moderate"] and risk.trend == "rising" or risk.is_elevated
    if not (always or elevated):
        return
    reply.risk = {
        "hazard": hazard,
        "level": risk.get_level_display(),
        "level_code": risk.level,
        "score": risk.score,
        "trend": risk.trend,
        "why": risk.explanation,
    }
    reply.facts.append(
        f"{risk.get_hazard_display()} risk in {lga.name} this week: {risk.get_level_display()} (score {risk.score}/100, {risk.trend}). Why: {risk.explanation}"
    )
    levels = phrase(reply.language, "levels")
    hazards = phrase(reply.language, "hazards")
    trend = phrase(reply.language, "trend_rising") if risk.trend == "rising" else ""
    reply.say("risk", hazard=hazards[hazard], lga=lga.name, level=levels[risk.level], trend=trend)
    reply.say(f"{hazard}_advice")


def _book_vaccine_reminder(reply, child, nd, today):
    remind_on = max(today, nd["due_date"] - timedelta(days=1))
    names = ", ".join(v.name for v in nd["vaccines"])
    alert, _ = Alert.objects.get_or_create(
        profile=reply.profile,
        dedupe_key=f"booked-vax-{child.id}-{nd['due_date'].isoformat()}",
        defaults={
            "kind": "reminder",
            "title": f"Reminder: {child.name}'s vaccines on {_fmt(nd['due_date'])}",
            "message": f"{child.name} is due for {names} on {_fmt(nd['due_date'])}. Bring the child health card.",
            "language": reply.language,
            "reason": "You asked Lafiya Care Navigator to remind you.",
            "scheduled_for": remind_on,
            "generated_by": "navigator",
        },
    )
    reply.reminder = {"id": alert.id, "title": alert.title, "date": _fmt(remind_on)}
    reply.say("reminder_booked", date=_fmt(remind_on))


def _topic(reply, key):
    topic = TOPICS[key]
    reply.topic = {"title": topic["title"], "points": topic["points"], "source": SOURCES[topic["source"]]}
    reply.guidance.extend(topic["points"])
    reply.sources.add(SOURCES[topic["source"]])


def handle(reply, intent, norm_text, today):
    p = reply.profile
    if intent == "vaccine":
        reply.sources.add(SOURCES["npi"])
        child = _pick_child(p, norm_text, today)
        if not child:
            reply.say("no_child")
            _add_facilities(reply, "immunization")
        else:
            nd = next_due(child, today)
            reply.facts.append(f"Child: {child.name}, age {child.age_display}, born {_fmt(child.date_of_birth)}.")
            if not nd:
                reply.facts.append(f"{child.name} has completed all scheduled vaccines.")
                reply.say("vaccine_done", child=child.name)
            else:
                names = ", ".join(v.name for v in nd["vaccines"])
                if nd["status"] == "overdue":
                    reply.facts.append(f"OVERDUE vaccines (due {_fmt(nd['due_date'])}): {names}.")
                    reply.say("vaccine_overdue", child=child.name, vaccines=names, date=_fmt(nd["due_date"]))
                else:
                    reply.facts.append(f"Next vaccines due {_fmt(nd['due_date'])}: {names}.")
                    reply.say("vaccine_next", child=child.name, vaccines=names, date=_fmt(nd["due_date"]))
                # Ground the model: it once called rotavirus a diabetes vaccine when not told.
                reply.facts.append(
                    "What they protect against: " + "; ".join(f"{v.name} - {v.protects_against}" for v in nd["vaccines"]) + "."
                )
                _book_vaccine_reminder(reply, child, nd, today)
            _add_facilities(reply, "immunization")
        _add_risk(reply, "malaria")
        return

    if intent == "pregnancy":
        _topic(reply, "pregnancy")
        preg = p.active_pregnancy
        if preg:
            visit = preg.next_visit()
            reply.facts.append(f"{p.first_name} is {preg.weeks} weeks pregnant, EDD {_fmt(preg.edd)}.")
            if visit:
                reply.facts.append(f"Next ANC contact {visit.contact_number} on {_fmt(visit.scheduled_date)}.")
                reply.say("pregnancy_status", weeks=preg.weeks, n=visit.contact_number, date=_fmt(visit.scheduled_date))
            danger = list(DangerSign.objects.filter(category="pregnancy").values_list("sign", flat=True))
            reply.guidance.append("Pregnancy danger signs — go to a facility at once: " + "; ".join(danger))
        else:
            reply.say("no_pregnancy")
        _add_facilities(reply, "antenatal")
        _add_risk(reply, "malaria")
        return

    if intent == "clinic":
        service = next((code for code, kws in CLINIC_SERVICE_KEYWORDS.items() if matches(norm_text, kws)), None)
        _add_facilities(reply, service)
        _add_risk(reply, "malaria")
        return

    if intent in ("malaria", "heat", "flood"):
        _topic(reply, intent)
        _add_risk(reply, intent, always=True)
        if not reply.risk:
            reply.say(f"{intent}_advice")
        _add_facilities(reply, SERVICE_FOR_INTENT[intent])
        return

    if intent in SYMPTOM_FOR_INTENT:
        symptom = SYMPTOMS[SYMPTOM_FOR_INTENT[intent]]
        reply.facts.append(f"The person reports: {symptom['reason'].split(' — ')[0].lower()}. Lafiya refers, never diagnoses.")
        if intent == "fever":
            reply.say("fever")
        if intent in TOPIC_FOR_INTENT:
            _topic(reply, TOPIC_FOR_INTENT[intent])
        _add_facilities(reply, symptom["service"], reason=symptom["reason"], urgency=symptom["urgency"])
        if intent == "fever":
            _add_risk(reply, "malaria")
        return

    if intent == "milestones":
        _topic(reply, "milestones")
        child = _pick_child(p, norm_text, today)
        if child:
            months = child.age_days(today) * 12 // 365
            ms = Milestone.objects.filter(age_months__lte=max(months, 1)).order_by("-age_months")[:4]
            reply.facts.append(f"Child {child.name} is {child.age_display}.")
            reply.guidance.extend(f"By {m.age_months} months: {m.description}" for m in ms)
        return

    if intent == "danger_signs":
        points = [f"{s.sign} ({s.get_category_display().lower()})." for s in DangerSign.objects.order_by("-category", "id")]
        reply.guidance.extend(points)
        reply.topic = {
            "title": "Danger signs — go to a facility immediately or call 112",
            "points": points,
            "source": SOURCES["who_imci"],
        }
        reply.sources.add(SOURCES["who_imci"])
        _add_facilities(reply, "emergency")
        return

    if intent in TOPIC_FOR_INTENT:
        _topic(reply, TOPIC_FOR_INTENT[intent])
        service = SERVICE_FOR_INTENT.get(intent)
        if service:
            _add_facilities(reply, service)
        if intent == "heat" or (intent == "hypertension" and p.lga):
            _add_risk(reply, "heat")
        return

    if intent == "greeting":
        reply.say("greeting", name=p.first_name)
        return
    if intent == "thanks":
        reply.say("thanks")
        return
    reply.say("fallback")


def respond(profile, text, language=None, conversation=None, today=None):
    today = today or date.today()
    language = language or profile.language
    norm = normalize(text)
    reply = Reply(profile, language)

    reply.emergency = detect_danger(norm)
    intent = detect_intent(norm)
    if reply.emergency:
        intent = intent if intent not in ("greeting", "thanks", "fallback") else "emergency"

    if reply.emergency:
        origin = profile.location()
        found = nearest_facilities(origin, service="emergency", limit=3) or nearest_facilities(origin, limit=3)
        if found:
            f, d = found[0]
            reply.parts.append(phrase(language, "emergency", facility=f.name, distance=d))
            reply.facilities = [facility_payload(fac, dist) for fac, dist in found]
            reply.referral = Referral.objects.create(
                profile=profile, facility=f, service="emergency", reason=f"Danger sign reported: {text[:150]}",
                urgency="emergency",
            )
            reply.facts.append(f"DANGER SIGN reported. Nearest emergency facility: {f.name} ({d} km), phone {f.phone or '112'}.")
        reply.sources.add(SOURCES["who_imci"])

    if reply.emergency:
        # Keep emergency replies short and unambiguous: only the urgent action.
        preg = profile.active_pregnancy
        if preg:
            reply.facts.append(f"The person is {preg.weeks} weeks pregnant.")
    else:
        handle(reply, intent, norm, today)

    # Speak: N-ATLAS writes the grounded reply; templates are the safety net.
    generated_by = "template"
    text_out = None
    if natlas.is_configured() and intent not in ("greeting", "thanks"):
        history = []
        if conversation:
            history = [(m.role, m.text) for m in conversation.messages.order_by("-created_at")[:6]][::-1]
        facts = [f"User: {profile.first_name}, LGA {profile.lga or 'unknown'}, language {language}."] + reply.facts
        text_out = natlas.compose(language, facts, reply.guidance, question=text, history=history)
        if text_out:
            generated_by = "n-atlas"
            if reply.emergency:  # never rely on the model alone for emergencies
                text_out = reply.parts[0] + "\n\n" + text_out
    if not text_out:
        parts = list(reply.parts)
        if reply.topic and intent in TOPIC_ONLY_INTENTS:
            # Lead with the guidance itself; the full list is shown as a card in the UI.
            intro = phrase(language, "topic_intro")
            parts.insert(0, (intro + " " if intro else "") + " ".join(reply.topic["points"][:2]))
        text_out = " ".join(parts) or phrase(language, "fallback")

    return {
        "reply": text_out,
        "language": language,
        "intent": intent,
        "emergency": reply.emergency,
        "generated_by": generated_by,
        "facilities": reply.facilities,
        "reminder": reply.reminder,
        "referral_id": reply.referral.id if reply.referral else None,
        "risk": reply.risk,
        "topic": reply.topic,
        "sources": sorted(reply.sources),
        "disclaimer": "Lafiya gives health information and referrals. It does not diagnose. In an emergency call 112.",
    }


def ask(profile, text, language=None, conversation_id=None, channel="web", input_mode="text", asr_engine="",
        conversation=None):
    """Persist the exchange (with validation evidence) and return the response payload."""
    started = time.monotonic()
    conv = conversation
    if conv is None and conversation_id:
        conv = Conversation.objects.filter(id=conversation_id, profile=profile).first()
    if conv is None:
        conv = Conversation.objects.create(profile=profile, channel=channel)
    result = respond(profile, text, language=language, conversation=conv)
    latency = int((time.monotonic() - started) * 1000)
    evidence = {"channel": channel, "input_mode": input_mode}
    Message.objects.create(
        conversation=conv, role="user", text=text, language=result["language"],
        asr_engine=asr_engine if input_mode == "voice" else "", **evidence,
    )
    answer = Message.objects.create(
        conversation=conv,
        role="assistant",
        text=result["reply"],
        language=result["language"],
        intent=result["intent"],
        emergency=result["emergency"],
        generated_by=result["generated_by"],
        latency_ms=latency,
        payload={k: v for k, v in result.items() if k != "reply"},
        **evidence,
    )
    result["conversation_id"] = conv.id
    result["message_id"] = answer.id
    result["latency_ms"] = latency
    return result
