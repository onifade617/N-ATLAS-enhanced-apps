"""The Lafiya Intelligence Loop: Sense → Match → Speak → Act → See."""

import logging
from collections import Counter
from datetime import date, timedelta

from django.conf import settings

from climateguard.models import RiskAssessment
from climateguard.risk import assess_many
from climateguard.weather import ingest_lgas
from core.geo import best_facility
from core.models import LGA, Profile
from immunitrack.services import next_due
from navigator import natlas

from .messages import render
from .models import Alert

log = logging.getLogger(__name__)

HAZARD_SERVICE = {"malaria": "malaria", "heat": "ncd", "flood": "emergency"}
REMINDER_WINDOW_DAYS = 3


def _week_key(today):
    y, w, _ = today.isocalendar()
    return f"{y}w{w}"


def sense(today=None, live=None, lgas=None):
    """Ingest weather and recompute risk for every LGA."""
    today = today or date.today()
    lgas = list(lgas or LGA.objects.all())
    sources = ingest_lgas(lgas, today, live=live)
    # Baseline from the same freshly ingested weather, so week-on-week trends compare like with like.
    assess_many(lgas, [today - timedelta(days=7), today])
    return sources


def at_risk_for(hazard, profile):
    """Match: does this hazard affect this person?"""
    pregnant = profile.active_pregnancy is not None
    has_u5 = bool(profile.under_five_children)
    if hazard == "malaria":
        return pregnant or has_u5
    if hazard == "heat":
        return pregnant or has_u5 or profile.has_hypertension or profile.has_diabetes
    return True  # flood affects every household


def why_matched(hazard, profile):
    groups = []
    if profile.active_pregnancy:
        groups.append("you are pregnant")
    if profile.under_five_children:
        groups.append("you care for a child under five")
    if hazard == "heat" and profile.has_hypertension:
        groups.append("you have high blood pressure")
    if hazard == "heat" and profile.has_diabetes:
        groups.append("you have diabetes")
    return " and ".join(groups) or "you live in this LGA"


class Speaker:
    """Speak: N-ATLAS writes the message; templates are the safety net."""

    def __init__(self, use_natlas=True, max_natlas=50):
        self.use_natlas = use_natlas and natlas.is_configured()
        self.remaining = max_natlas
        self.cache = {}

    def speak(self, key, language, facts, cache_key=None, **ctx):
        text, title = render(key, language, **ctx)
        if not self.use_natlas:
            return text, title, "template"
        if cache_key and cache_key in self.cache:
            return self.cache[cache_key], title, "n-atlas"
        if self.remaining <= 0:
            return text, title, "template"
        self.remaining -= 1
        generated = natlas.compose(language, facts + [f"Reference message: {text}"], [])
        if not generated:
            return text, title, "template"
        if cache_key:
            self.cache[cache_key] = generated
        return generated, title, "n-atlas"


def _create(profile, dedupe_key, **fields):
    alert, created = Alert.objects.get_or_create(profile=profile, dedupe_key=dedupe_key, defaults=fields)
    if created:
        from navigator.whatsapp import deliver_alert  # Act: push to WhatsApp when the person uses it

        deliver_alert(alert)
    return created


def climate_alerts(speaker, today):
    created = Counter()
    risks = RiskAssessment.objects.filter(date=today, level__in=["high", "very_high"]).select_related("lga")
    for risk in risks:
        profiles = Profile.objects.filter(lga=risk.lga, consent_given=True, role=Profile.ROLE_FAMILY)
        for p in profiles.prefetch_related("children", "pregnancies"):
            if not at_risk_for(risk.hazard, p):
                continue
            fac = best_facility(p.location(), HAZARD_SERVICE[risk.hazard])
            facility = fac[0] if fac else None
            fname = facility.name if facility else "your nearest health facility"
            ctx = {
                "lga": risk.lga.name,
                "facility": fname,
                "temp": round(risk.inputs.get("peak_feels_like_c", 0)),
                "rain": round(risk.inputs.get("max_3day_rain_mm", 0)),
            }
            facts = [
                f"Person: {p.first_name}; {why_matched(risk.hazard, p)}.",
                f"{risk.get_hazard_display()} risk in {risk.lga.name} is {risk.get_level_display()} (score {risk.score}/100, trend {risk.trend}).",
                f"Why: {risk.explanation}",
                f"Nearest suitable facility: {fname}.",
            ]
            message, title, gen = speaker.speak(
                risk.hazard, p.language, facts,
                cache_key=(risk.hazard, risk.lga_id, p.language, facility.id if facility else None), **ctx,
            )
            if _create(
                p,
                f"{risk.hazard}-{risk.lga_id}-{_week_key(today)}",
                kind=risk.hazard,
                title=title,
                message=message,
                language=p.language,
                reason=f"{risk.explanation} You received this because {why_matched(risk.hazard, p)}.",
                facility=facility,
                scheduled_for=today,
                generated_by=gen,
            ):
                created[risk.hazard] += 1
    return created


def care_reminders(speaker, today):
    created = Counter()
    profiles = Profile.objects.filter(consent_given=True, role=Profile.ROLE_FAMILY).prefetch_related(
        "children__immunizations__vaccine", "pregnancies__visits"
    )
    for p in profiles:
        origin = p.location()
        for child in p.children.all():
            if not child.is_under_five:
                continue
            nd = next_due(child, today)
            if not nd or nd["due_date"] > today + timedelta(days=REMINDER_WINDOW_DAYS):
                continue
            overdue = nd["status"] == "overdue"
            fac = best_facility(origin, "immunization")
            fname = fac[0].name if fac else "your nearest health facility"
            names = ", ".join(v.name for v in nd["vaccines"])
            key = "vaccine_overdue" if overdue else "vaccine"
            ctx = {"child": child.name, "vaccines": names, "date": nd["due_date"].strftime("%d %b"), "facility": fname}
            facts = [
                f"Caregiver: {p.first_name}. Child: {child.name}, age {child.age_display}.",
                f"Vaccines {'overdue since' if overdue else 'due on'} {ctx['date']}: {names}.",
                f"Nearest immunization facility: {fname}. Immunization is free.",
            ]
            message, title, gen = speaker.speak(key, p.language, facts, **ctx)
            if _create(
                p,
                f"vax-{child.id}-{nd['due_date'].isoformat()}",
                kind="vaccine",
                title=title,
                message=message,
                language=p.language,
                reason=f"Based on the national routine immunization schedule and {child.name}'s date of birth.",
                facility=fac[0] if fac else None,
                scheduled_for=today,
                generated_by=gen,
            ):
                created["vaccine"] += 1
        preg = p.active_pregnancy
        if preg:
            visit = preg.next_visit()
            if visit and visit.scheduled_date <= today + timedelta(days=REMINDER_WINDOW_DAYS):
                fac = best_facility(origin, "antenatal")
                fname = fac[0].name if fac else "your nearest health facility"
                ctx = {
                    "n": visit.contact_number,
                    "week": visit.gestation_week,
                    "date": visit.scheduled_date.strftime("%d %b"),
                    "facility": fname,
                }
                facts = [
                    f"Mother: {p.first_name}, {preg.weeks} weeks pregnant.",
                    f"ANC contact {visit.contact_number} (week {visit.gestation_week}) due {ctx['date']}.",
                    f"Nearest antenatal facility: {fname}.",
                ]
                message, title, gen = speaker.speak("anc", p.language, facts, **ctx)
                if _create(
                    p,
                    f"anc-{visit.id}",
                    kind="anc",
                    title=title,
                    message=message,
                    language=p.language,
                    reason="WHO recommends 8 antenatal contacts; this is based on your last menstrual period.",
                    facility=fac[0] if fac else None,
                    scheduled_for=today,
                    generated_by=gen,
                ):
                    created["anc"] += 1
    return created


def run_loop(today=None, refresh_weather=True, live=None, use_natlas=None, max_natlas=50):
    today = today or date.today()
    if use_natlas is None:
        use_natlas = settings.NATLAS_FOR_ALERTS
    summary = {}
    if refresh_weather:
        summary["weather_sources"] = sense(today, live=live)
    speaker = Speaker(use_natlas=use_natlas, max_natlas=max_natlas)
    created = climate_alerts(speaker, today)
    created.update(care_reminders(speaker, today))
    summary["alerts_created"] = dict(created)
    if speaker.use_natlas:
        summary["generated_with"] = "N-ATLAS"
    elif use_natlas:
        summary["generated_with"] = "templates (N-ATLAS not configured)"
    else:
        summary["generated_with"] = "templates (N-ATLaS alerts off to save GPU credit)"
    return summary
