from datetime import timedelta

from django.shortcuts import render

from core.forms import grouped_lga_choices
from core.models import LGA

from .risk import METHODOLOGY, latest_risks


def risk_view(request):
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    lga = None
    if request.GET.get("lga"):
        lga = LGA.objects.filter(pk=request.GET["lga"]).first()
    if lga is None and profile and profile.lga:
        lga = profile.lga
    if lga is None:
        lga = LGA.objects.first()
    risks = latest_risks(lga) if lga else {}
    weather = []
    if risks:
        as_of = max(r.date for r in risks.values())
        weather = list(lga.weather.filter(date__gte=as_of - timedelta(days=14)).order_by("date"))
    chart = {
        "labels": [w.date.strftime("%d %b") for w in weather],
        "rain": [w.precipitation_mm for w in weather],
        "tmax": [w.apparent_temp_max for w in weather],
        "forecast": [w.is_forecast for w in weather],
    }
    return render(
        request,
        "climateguard/risk.html",
        {
            "lga": lga,
            "risks": [risks[h] for h in ("malaria", "heat", "flood") if h in risks],
            "methodology": METHODOLOGY,
            "chart": chart,
            "source": weather[-1].source if weather else None,
            "lga_choices": grouped_lga_choices()[1:],  # drop the "Select your LGA" placeholder
        },
    )
