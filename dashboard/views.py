import csv
import logging
import threading
from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.db import connection, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from alerts.engine import run_loop
from climateguard.risk import latest_risks
from core.decorators import role_required
from core.forms import CONSENT_TEXT, StyledMixin
from core.geo import facility_payload
from core.models import LANGUAGES, Child, Facility, Profile, State
from immunitrack.models import Immunization
from immunitrack.services import next_due
from mamacare.models import ANCVisit, Pregnancy
from navigator.models import Referral

from . import evidence
from .metrics import PUBLIC_FIELDS, kpis, lga_summary, public_row

log = logging.getLogger(__name__)

WORKER = Profile.ROLE_WORKER
GOV = Profile.ROLE_GOV


# ---------------------------------------------------------------- health worker


def _worker_lga(profile):
    return profile.facility.lga if profile.facility else profile.lga


@role_required(WORKER, GOV)
def worker_dashboard(request, profile):
    lga = _worker_lga(profile)
    today = date.today()
    window = today + timedelta(days=7)
    families = Profile.objects.filter(lga=lga, role=Profile.ROLE_FAMILY)

    children_due = []
    for child in Child.objects.filter(caregiver__in=families).select_related("caregiver").prefetch_related(
        "immunizations__vaccine"
    ):
        if not child.is_under_five:
            continue
        nd = next_due(child, today)
        if nd and nd["due_date"] <= window:
            children_due.append({"child": child, "next": nd})
    children_due.sort(key=lambda x: (x["next"]["status"] != "overdue", x["next"]["due_date"]))

    mothers = []
    for preg in Pregnancy.objects.filter(profile__in=families, active=True).select_related("profile"):
        visit = preg.next_visit()
        if visit and visit.scheduled_date <= window:
            mothers.append({"pregnancy": preg, "visit": visit, "status": visit.status(today)})
    mothers.sort(key=lambda x: (x["status"] != "overdue", not x["pregnancy"].high_risk, x["visit"].scheduled_date))

    risks = latest_risks(lga) if lga else {}
    elevated = [r for r in risks.values() if r.is_elevated]
    referrals = Referral.objects.filter(facility__lga=lga, status__in=["suggested", "accepted"]).select_related(
        "profile", "facility"
    )[:30]
    return render(
        request,
        "dashboard/worker.html",
        {
            "lga": lga,
            "children_due": children_due,
            "mothers": mothers,
            "elevated": elevated,
            "risks": [risks[h] for h in ("malaria", "heat", "flood") if h in risks],
            "referrals": referrals,
            "pregnant_count": Pregnancy.objects.filter(profile__in=families, active=True).count(),
            "u5_count": sum(1 for c in Child.objects.filter(caregiver__in=families) if c.is_under_five),
            "today": today,
        },
    )


@require_POST
@role_required(WORKER, GOV)
def worker_vaccinate(request, profile, child_id):
    child = get_object_or_404(Child, pk=child_id, caregiver__lga=_worker_lga(profile))
    nd = next_due(child)
    if nd:
        for v in nd["vaccines"]:
            Immunization.objects.update_or_create(
                child=child, vaccine=v,
                defaults={"given_date": date.today(), "facility": profile.facility, "recorded_by": profile},
            )
        messages.success(request, f"Recorded {', '.join(v.name for v in nd['vaccines'])} for {child.name}.")
    return redirect("worker_dashboard")


@require_POST
@role_required(WORKER, GOV)
def worker_anc(request, profile, visit_id):
    visit = get_object_or_404(ANCVisit, pk=visit_id, pregnancy__profile__lga=_worker_lga(profile))
    visit.attended_date = date.today()
    visit.facility = profile.facility
    visit.save(update_fields=["attended_date", "facility"])
    messages.success(request, f"ANC contact {visit.contact_number} recorded for {visit.pregnancy.profile}.")
    return redirect("worker_dashboard")


@require_POST
@role_required(WORKER, GOV)
def worker_flag(request, profile, pregnancy_id):
    preg = get_object_or_404(Pregnancy, pk=pregnancy_id, profile__lga=_worker_lga(profile))
    preg.high_risk = not preg.high_risk
    preg.save(update_fields=["high_risk"])
    return redirect("worker_dashboard")


@require_POST
@role_required(WORKER, GOV)
def worker_referral_done(request, profile, referral_id):
    ref = get_object_or_404(Referral, pk=referral_id, facility__lga=_worker_lga(profile))
    ref.status = "completed"
    ref.completed_at = timezone.now()
    ref.save(update_fields=["status", "completed_at"])
    messages.success(request, f"Referral for {ref.profile} marked completed.")
    return redirect("worker_dashboard")


class EnrolForm(StyledMixin, forms.Form):
    full_name = forms.CharField(max_length=120)
    phone = forms.CharField(max_length=20, required=False)
    language = forms.ChoiceField(choices=LANGUAGES)
    has_hypertension = forms.BooleanField(required=False, label="Has high blood pressure")
    has_diabetes = forms.BooleanField(required=False, label="Has diabetes")
    lmp_date = forms.DateField(required=False, label="If pregnant: first day of last period",
                               widget=forms.DateInput(attrs={"type": "date"}))
    child_name = forms.CharField(required=False, label="Child's name (under 5)")
    child_sex = forms.ChoiceField(choices=[("", "—")] + Child.SEX, required=False, label="Child's sex")
    child_dob = forms.DateField(required=False, label="Child's date of birth", widget=forms.DateInput(attrs={"type": "date"}))
    consent = forms.BooleanField(label="The person has heard and agreed to: " + CONSENT_TEXT)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean(self):
        data = super().clean()
        if data.get("child_name") and not (data.get("child_dob") and data.get("child_sex")):
            raise forms.ValidationError("Please give the child's sex and date of birth.")
        return data


@role_required(WORKER, GOV)
def worker_enrol(request, profile):
    form = EnrolForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            person = Profile.objects.create(
                full_name=d["full_name"], phone=d["phone"], language=d["language"], lga=_worker_lga(profile),
                has_hypertension=d["has_hypertension"], has_diabetes=d["has_diabetes"],
                consent_given=True, consent_at=timezone.now(), enrolled_by=profile,
            )
            if d.get("lmp_date"):
                Pregnancy.objects.create(profile=person, lmp_date=d["lmp_date"])
            if d.get("child_name"):
                Child.objects.create(caregiver=person, name=d["child_name"], sex=d["child_sex"], date_of_birth=d["child_dob"])
        messages.success(request, f"{person.full_name} enrolled. Reminders will be sent in {person.language_name}.")
        return redirect("worker_dashboard")
    return render(request, "dashboard/enrol.html", {"form": form})


# ------------------------------------------------------------------ government


def _state_filter(request):
    sid = request.GET.get("state")
    return State.objects.filter(pk=sid).first() if sid else None


@role_required(GOV)
def gov_dashboard(request, profile):
    state = _state_filter(request)
    rows = lga_summary(state)
    return render(
        request,
        "dashboard/gov.html",
        {
            "rows": rows,
            # Nationally, list only LGAs with enrolled families; a state filter lists all of its LGAs.
            "table_rows": rows if state else [r for r in rows if r["enrolled"] or r["children_u5"]],
            "kpi": kpis(rows, state),
            "states": State.objects.all(),
            "state": state,
            # Light map layer: hospitals only (the full ~55,000 list is available via the API).
            "facilities": [
                [round(f.latitude, 5), round(f.longitude, 5), f.name, f.get_facility_type_display()]
                for f in Facility.objects.filter(facility_type__in=Facility.HOSPITAL_TYPES).only(
                    "latitude", "longitude", "name", "facility_type")
            ],
            "evidence": evidence.summary(),
        },
    )


@role_required(GOV)
def gov_evidence_export(request, profile):
    """Anonymised real-user interaction log (no message text) for the NAIC validation evidence."""
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="lafiya-evidence-{date.today()}.csv"'
    evidence.write_csv(resp)
    return resp


@role_required(GOV)
def gov_export(request, profile):
    state = _state_filter(request)
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="lafiya-lga-report-{date.today()}.csv"'
    writer = csv.DictWriter(resp, fieldnames=PUBLIC_FIELDS)
    writer.writeheader()
    for row in lga_summary(state):
        writer.writerow(public_row(row))
    return resp


_loop_lock = threading.Lock()


def _run_loop_in_background():
    try:
        summary = run_loop(refresh_weather=True)
        log.info("Intelligence Loop finished: %s", summary)
    except Exception:
        log.exception("Intelligence Loop failed")
    finally:
        connection.close()
        _loop_lock.release()


@require_POST
@role_required(GOV)
def gov_run_loop(request, profile):
    """Weather for all 774 LGAs can take a few minutes (API rate limits), so run it in the background."""
    if not _loop_lock.acquire(blocking=False):
        messages.info(request, "The Intelligence Loop is already running — refresh in a minute or two.")
        return redirect("gov_dashboard")
    threading.Thread(target=_run_loop_in_background, daemon=True).start()
    messages.success(
        request,
        "Intelligence Loop started for all 774 LGAs: weather → risk → personalised alerts. "
        "Refresh this page in 1–3 minutes to see the updated map.",
    )
    return redirect("gov_dashboard")


# ------------------------------------------------------------------ open API


def api_index(request):
    base = request.build_absolute_uri("/api/v1/")
    return JsonResponse(
        {
            "name": "Lafiya AI open data API",
            "description": "Anonymised, aggregated indicators by LGA. Counts below "
            "the minimum cell size are suppressed (Nigeria Data Protection Act 2023).",
            "endpoints": {
                "lgas": base + "lgas/?state=<id>",
                "facilities": base + "facilities/?state=<id>&lga=<id>&service=<code>&limit=500&offset=0",
                "states": base + "states/",
            },
        }
    )


def api_lgas(request):
    state = _state_filter(request)
    return JsonResponse({"generated": date.today().isoformat(), "results": [public_row(r) for r in lga_summary(state)]})


def api_facilities(request):
    """Facilities, filterable by ?state=<id>&lga=<id>&service=<code>&type=<code>; paginated with ?limit=&offset=."""
    qs = Facility.objects.select_related("lga").order_by("id")
    if request.GET.get("state"):
        qs = qs.filter(lga__state_id=request.GET["state"])
    if request.GET.get("lga"):
        qs = qs.filter(lga_id=request.GET["lga"])
    if request.GET.get("service"):
        qs = qs.filter(services__contains=request.GET["service"])
    if request.GET.get("type"):
        qs = qs.filter(facility_type=request.GET["type"])
    try:
        limit = max(1, min(int(request.GET.get("limit", 500)), 5000))
        offset = max(0, int(request.GET.get("offset", 0)))
    except ValueError:
        return JsonResponse({"error": "limit and offset must be integers"}, status=400)
    return JsonResponse({
        "count": qs.count(), "limit": limit, "offset": offset,
        "source": "GRID3 Nigeria health facilities v3.0/v2.0 (Nigeria Health Facility Registry, NPHCDA), CC BY 4.0; "
                  "hours and services are typical for the facility type, not confirmed",
        "results": [facility_payload(f) for f in qs[offset:offset + limit]],
    })


def api_states(request):
    return JsonResponse({"results": [{"id": s.id, "name": s.name, "code": s.code} for s in State.objects.all()]})
