from datetime import date

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import profile_required

from .models import Alert


@profile_required
def inbox(request, profile):
    today = date.today()
    alerts = profile.alerts.select_related("facility")
    return render(
        request,
        "alerts/inbox.html",
        {
            "current": alerts.filter(scheduled_for__lte=today),
            "upcoming": alerts.filter(scheduled_for__gt=today).order_by("scheduled_for"),
        },
    )


@require_POST
@profile_required
def mark_opened(request, profile, pk):
    alert = get_object_or_404(Alert, pk=pk, profile=profile)
    if not alert.opened_at:
        alert.opened_at = timezone.now()
        alert.save(update_fields=["opened_at"])
    return JsonResponse({"ok": True})


@require_POST
@profile_required
def mark_acted(request, profile, pk):
    alert = get_object_or_404(Alert, pk=pk, profile=profile)
    now = timezone.now()
    alert.opened_at = alert.opened_at or now
    alert.acted_on_at = alert.acted_on_at or now
    alert.save(update_fields=["opened_at", "acted_on_at"])
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"ok": True})
    return redirect("alerts")
