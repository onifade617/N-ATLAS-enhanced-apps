"""Aggregated, anonymised indicators for government dashboards, exports and the open API."""

from collections import Counter, defaultdict
from datetime import date

from django.conf import settings
from django.db.models import Count, Q

from alerts.models import Alert
from climateguard.models import RiskAssessment
from core.models import LANGUAGE_NAMES, LGA, Child, Profile
from immunitrack.services import coverage_for_children
from mamacare.models import ANCVisit, Pregnancy
from navigator.models import Referral


def suppress(n):
    """Hide small non-zero counts so individuals cannot be re-identified."""
    if n is None:
        return None
    return n if n == 0 or n >= settings.ANON_MIN_CELL else f"<{settings.ANON_MIN_CELL}"


def latest_risk_map(lgas):
    out = defaultdict(dict)
    for ra in RiskAssessment.objects.filter(lga__in=lgas).order_by("lga_id", "hazard", "-date"):
        out[ra.lga_id].setdefault(ra.hazard, ra)
    return out


def lga_summary(state=None, today=None):
    today = today or date.today()
    lgas = LGA.objects.select_related("state")
    if state:
        lgas = lgas.filter(state=state)
    lgas = list(lgas)
    risks = latest_risk_map(lgas)

    families = Profile.objects.filter(role=Profile.ROLE_FAMILY, consent_given=True)
    enrolled = dict(families.values_list("lga").annotate(n=Count("id")))
    pregnant = dict(
        Pregnancy.objects.filter(active=True).values_list("profile__lga").annotate(n=Count("id"))
    )
    children_by_lga = defaultdict(list)
    for child in Child.objects.select_related("caregiver").prefetch_related("immunizations__vaccine"):
        children_by_lga[child.caregiver.lga_id].append(child)
    alerts = {
        row["profile__lga"]: row
        for row in Alert.objects.exclude(kind="reminder")
        .values("profile__lga")
        .annotate(sent=Count("id"), opened=Count("id", filter=Q(opened_at__isnull=False)),
                  acted=Count("id", filter=Q(acted_on_at__isnull=False)))
    }
    refs = {
        row["facility__lga"]: row
        for row in Referral.objects.values("facility__lga").annotate(
            total=Count("id"), completed=Count("id", filter=Q(status="completed"))
        )
    }
    anc = {
        row["pregnancy__profile__lga"]: row
        for row in ANCVisit.objects.filter(scheduled_date__lte=today)
        .values("pregnancy__profile__lga")
        .annotate(due=Count("id"), attended=Count("id", filter=Q(attended_date__isnull=False)))
    }

    rows = []
    for lga in lgas:
        cov = coverage_for_children(children_by_lga.get(lga.id, []), today)
        a = alerts.get(lga.id, {})
        r = refs.get(lga.id, {})
        v = anc.get(lga.id, {})
        lr = risks.get(lga.id, {})
        rows.append(
            {
                "lga_id": lga.id,
                "lga": lga.name,
                "state": lga.state.name,
                "lat": lga.latitude,
                "lon": lga.longitude,
                "enrolled": enrolled.get(lga.id, 0),
                "pregnant": pregnant.get(lga.id, 0),
                "children_u5": cov["children"],
                "penta1_coverage": cov.get("penta1_coverage"),
                "penta3_coverage": cov.get("penta3_coverage"),
                "mcv1_coverage": cov.get("mcv1_coverage"),
                "zero_dose": cov["zero_dose"],
                "dropout_penta1_3": cov.get("dropout_penta1_3"),
                "anc_due": v.get("due", 0),
                "anc_attended": v.get("attended", 0),
                "alerts_sent": a.get("sent", 0),
                "alerts_opened": a.get("opened", 0),
                "alerts_acted": a.get("acted", 0),
                "referrals": r.get("total", 0),
                "referrals_completed": r.get("completed", 0),
                **{
                    f"{h}_level": (lr[h].level if h in lr else None)
                    for h in ("malaria", "heat", "flood")
                },
                **{
                    f"{h}_score": (lr[h].score if h in lr else None)
                    for h in ("malaria", "heat", "flood")
                },
                **{
                    f"{h}_why": (lr[h].explanation if h in lr else "")
                    for h in ("malaria", "heat", "flood")
                },
            }
        )
    return rows


def pct(num, den):
    return round(100 * num / den) if den else None


def kpis(rows, state=None):
    total = Counter()
    for r in rows:
        for k in ("enrolled", "pregnant", "children_u5", "zero_dose", "anc_due", "anc_attended", "alerts_sent",
                  "alerts_opened", "alerts_acted", "referrals", "referrals_completed"):
            total[k] += r[k]
    families = Profile.objects.filter(role=Profile.ROLE_FAMILY, consent_given=True)
    if state:
        families = families.filter(lga__state=state)
    by_lang = Counter(families.values_list("language", flat=True))
    children = Child.objects.prefetch_related("immunizations__vaccine")
    if state:
        children = children.filter(caregiver__lga__state=state)
    cov = coverage_for_children(children)
    elevated = sum(
        1 for r in rows if any(r[f"{h}_level"] in ("high", "very_high") for h in ("malaria", "heat", "flood"))
    )
    return {
        **total,
        "by_language": [(LANGUAGE_NAMES[k], v) for k, v in by_lang.most_common()],
        "penta3_coverage": cov.get("penta3_coverage"),
        "penta1_coverage": cov.get("penta1_coverage"),
        "mcv1_coverage": cov.get("mcv1_coverage"),
        "anc_attendance": pct(total["anc_attended"], total["anc_due"]),
        "alert_open_rate": pct(total["alerts_opened"], total["alerts_sent"]),
        "alert_action_rate": pct(total["alerts_acted"], total["alerts_sent"]),
        "referral_completion": pct(total["referrals_completed"], total["referrals"]),
        "lgas_elevated": elevated,
        "lgas": len(rows),
    }


PUBLIC_FIELDS = [
    "state", "lga", "lat", "lon", "enrolled", "pregnant", "children_u5", "penta1_coverage", "penta3_coverage",
    "mcv1_coverage", "zero_dose", "dropout_penta1_3", "anc_due", "anc_attended", "alerts_sent", "alerts_opened",
    "alerts_acted", "referrals", "referrals_completed", "malaria_level", "malaria_score", "heat_level", "heat_score",
    "flood_level", "flood_score",
]
COUNT_FIELDS = {"enrolled", "pregnant", "children_u5", "zero_dose", "anc_due", "anc_attended", "alerts_sent",
                "alerts_opened", "alerts_acted", "referrals", "referrals_completed"}


def public_row(row):
    return {k: (suppress(row[k]) if k in COUNT_FIELDS else row[k]) for k in PUBLIC_FIELDS}
