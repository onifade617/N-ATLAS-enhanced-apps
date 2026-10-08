import json
from datetime import date

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from climateguard.risk import latest_risks
from immunitrack.services import next_due

from .decorators import profile_required
from .forms import FacilitySearchForm, ProfileForm, SignupForm
from .geo import facility_payload, nearest_facilities
from .models import Profile


def landing(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "core/landing.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            Profile.objects.create(
                user=user,
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data["phone"],
                language=form.cleaned_data["language"],
                lga=form.cleaned_data["lga"],
                has_hypertension=form.cleaned_data["has_hypertension"],
                has_diabetes=form.cleaned_data["has_diabetes"],
                consent_given=True,
                consent_at=timezone.now(),
            )
        login(request, user)
        messages.success(request, "Welcome to Lafiya! Add your pregnancy or children to get personal reminders.")
        return redirect("home")
    return render(request, "core/signup.html", {"form": form})


@login_required
def profile_setup(request):
    if hasattr(request.user, "profile"):
        return redirect("profile")
    form = ProfileForm(request.POST or None, initial={"full_name": request.user.get_full_name() or request.user.username})
    if request.method == "POST" and form.is_valid():
        profile = form.save(commit=False)
        profile.user = request.user
        profile.role = Profile.ROLE_GOV if request.user.is_staff else Profile.ROLE_FAMILY
        profile.consent_given = True
        profile.consent_at = timezone.now()
        profile.save()
        return redirect("home")
    return render(request, "core/profile.html", {"form": form, "setup": True})


@profile_required
def profile_view(request, profile):
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "core/profile.html", {"form": form})


@profile_required
def export_my_data(request, profile):
    """NDPA: data portability — everything Lafiya holds about this person."""
    data = {
        "profile": {
            "full_name": profile.full_name,
            "phone": profile.phone,
            "language": profile.language,
            "lga": str(profile.lga) if profile.lga else None,
            "has_hypertension": profile.has_hypertension,
            "has_diabetes": profile.has_diabetes,
            "consent_at": profile.consent_at.isoformat() if profile.consent_at else None,
        },
        "pregnancies": [
            {
                "lmp": p.lmp_date.isoformat(),
                "edd": p.edd.isoformat(),
                "active": p.active,
                "visits": [
                    {"contact": v.contact_number, "scheduled": v.scheduled_date.isoformat(),
                     "attended": v.attended_date.isoformat() if v.attended_date else None}
                    for v in p.visits.all()
                ],
            }
            for p in profile.pregnancies.all()
        ],
        "children": [
            {
                "name": c.name,
                "sex": c.sex,
                "date_of_birth": c.date_of_birth.isoformat(),
                "immunizations": [
                    {"vaccine": i.vaccine.name, "date": i.given_date.isoformat()} for i in c.immunizations.all()
                ],
            }
            for c in profile.children.all()
        ],
        "alerts": [
            {"title": a.title, "message": a.message, "date": a.scheduled_for.isoformat()} for a in profile.alerts.all()
        ],
        "conversations": [
            [{"role": m.role, "text": m.text, "at": m.created_at.isoformat()} for m in conv.messages.all()]
            for conv in profile.conversations.all()
        ],
    }
    resp = HttpResponse(json.dumps(data, indent=2, ensure_ascii=False), content_type="application/json")
    resp["Content-Disposition"] = 'attachment; filename="my-lafiya-data.json"'
    return resp


@require_POST
@profile_required
def delete_my_data(request, profile):
    """NDPA: right to erasure. Removes the profile, all health records and the login."""
    user = request.user
    logout(request)
    profile.delete()
    user.delete()
    messages.success(request, "Your account and all your health data have been deleted.")
    return redirect("landing")


@profile_required
def home(request, profile):
    if profile.is_worker and request.GET.get("view") != "family":
        return redirect("worker_dashboard")
    if profile.is_government and request.GET.get("view") != "family":
        return redirect("gov_dashboard")
    today = date.today()
    children = []
    for child in profile.children.all():
        if child.is_under_five:
            children.append({"child": child, "next": next_due(child, today)})
    preg = profile.active_pregnancy
    risks = latest_risks(profile.lga) if profile.lga else {}
    nearest = nearest_facilities(profile.location(), limit=3)
    alerts = profile.alerts.filter(scheduled_for__lte=today)[:5]
    return render(
        request,
        "core/home.html",
        {
            "children": children,
            "pregnancy": preg,
            "next_visit": preg.next_visit() if preg else None,
            "risks": [risks[h] for h in ("malaria", "heat", "flood") if h in risks],
            "nearest": nearest,
            "alerts": alerts,
        },
    )


def facility_finder(request):
    form = FacilitySearchForm(request.GET or None)
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    origin = None
    service = None
    open_now = False
    if form.is_valid():
        service = form.cleaned_data["service"] or None
        open_now = form.cleaned_data["open_now"]
        if form.cleaned_data["lat"] is not None and form.cleaned_data["lon"] is not None:
            origin = (form.cleaned_data["lat"], form.cleaned_data["lon"])
    if origin is None and profile:
        origin = profile.location()
    if origin is None:
        origin = (6.5244, 3.3792)  # Lagos default
    results = nearest_facilities(origin, service=service, limit=15, open_now_only=open_now)
    payload = [facility_payload(f, d) for f, d in results]
    return render(
        request,
        "core/facilities.html",
        {"form": form, "results": results, "payload": payload, "origin": origin},
    )
