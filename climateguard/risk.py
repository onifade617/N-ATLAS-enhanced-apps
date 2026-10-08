"""Transparent, explainable climate-health risk scores per LGA.

Every threshold below is published on the ClimateGuard page and every score
carries a plain-language explanation of *why*.
"""

from datetime import date, timedelta

from .models import RiskAssessment, WeatherDay

METHODOLOGY = {
    "malaria": {
        "summary": "Malaria transmission rises 1–3 weeks after rain when it is warm and humid. "
        "Score = temperature suitability (0–40) + 14-day rainfall (0–35) + humidity (0–25).",
        "rules": [
            "Mean temperature 25–30°C: 40 pts · 22–25 or 30–32°C: 25 · 18–22 or 32–34°C: 10",
            "Rain in last 14 days ≥80 mm: 35 pts · ≥40 mm: 25 · ≥10 mm: 12",
            "Mean humidity ≥70%: 25 pts · ≥60%: 15 · ≥50%: 5",
            "Level: <30 low · 30–54 moderate · 55–74 high · ≥75 very high",
        ],
    },
    "heat": {
        "summary": "Based on the hottest 'feels-like' temperature forecast for the next 7 days "
        "(heat-index bands used by public-health agencies).",
        "rules": [
            "Feels-like <32°C: low · 32–37.9°C: moderate · 38–40.9°C: high · ≥41°C: very high",
            "Three or more days at ≥38°C raises the level by one step",
        ],
    },
    "flood": {
        "summary": "Based on the wettest 3-day rainfall total in the last 3 days and next 7 days.",
        "rules": [
            "3-day rain ≥100 mm: very high · ≥60 mm: high · ≥30 mm: moderate · else low",
            "Any single day ≥50 mm raises the level to at least high",
        ],
    },
}

LEVELS = ["low", "moderate", "high", "very_high"]


def _bump(level, steps=1):
    return LEVELS[min(len(LEVELS) - 1, LEVELS.index(level) + steps)]


def _clamp(x):
    return int(max(0, min(100, round(x))))


def malaria_risk(past):
    if not past:
        return None
    mean_t = sum((d.temp_max + d.temp_min) / 2 for d in past) / len(past)
    rain = sum(d.precipitation_mm for d in past)
    hum = sum(d.humidity_mean for d in past) / len(past)
    if 25 <= mean_t <= 30:
        t_pts = 40
    elif 22 <= mean_t < 25 or 30 < mean_t <= 32:
        t_pts = 25
    elif 18 <= mean_t < 22 or 32 < mean_t <= 34:
        t_pts = 10
    else:
        t_pts = 0
    r_pts = 35 if rain >= 80 else 25 if rain >= 40 else 12 if rain >= 10 else 0
    h_pts = 25 if hum >= 70 else 15 if hum >= 60 else 5 if hum >= 50 else 0
    score = t_pts + r_pts + h_pts
    level = "very_high" if score >= 75 else "high" if score >= 55 else "moderate" if score >= 30 else "low"
    explanation = (
        f"{rain:.0f} mm of rain fell in the last 14 days, average temperature was {mean_t:.1f}°C "
        f"and humidity {hum:.0f}% — "
        + (
            "ideal conditions for mosquitoes to breed."
            if score >= 55
            else "some conditions for mosquito breeding."
            if score >= 30
            else "conditions are less favourable for mosquitoes."
        )
    )
    inputs = {"mean_temp_c": round(mean_t, 1), "rain_14d_mm": round(rain, 1), "humidity_pct": round(hum)}
    return score, level, explanation, inputs


def heat_risk(forecast):
    if not forecast:
        return None
    peak = max(d.apparent_temp_max for d in forecast)
    hot_days = sum(1 for d in forecast if d.apparent_temp_max >= 38)
    level = "very_high" if peak >= 41 else "high" if peak >= 38 else "moderate" if peak >= 32 else "low"
    if hot_days >= 3 and level != "very_high":
        level = _bump(level)
    score = _clamp((peak - 26) * 5 + hot_days * 3)
    explanation = f"It will feel as hot as {peak:.0f}°C in the next 7 days" + (
        f", with {hot_days} day{'s' if hot_days != 1 else ''} at 38°C or more." if hot_days else "."
    )
    return score, level, explanation, {"peak_feels_like_c": round(peak, 1), "days_ge_38c": hot_days}


def flood_risk(days):
    if len(days) < 3:
        return None
    rains = [d.precipitation_mm for d in days]
    best = max(sum(rains[i : i + 3]) for i in range(len(rains) - 2))
    max_day = max(rains)
    level = "very_high" if best >= 100 else "high" if best >= 60 else "moderate" if best >= 30 else "low"
    if max_day >= 50 and LEVELS.index(level) < LEVELS.index("high"):
        level = "high"
    score = _clamp(best * 0.9)
    explanation = f"Up to {best:.0f} mm of rain in 3 days is recorded or forecast (heaviest day {max_day:.0f} mm)."
    return score, level, explanation, {"max_3day_rain_mm": round(best, 1), "max_day_rain_mm": round(max_day, 1)}


def compute(lga, today, weather):
    """Unsaved RiskAssessments for one LGA and day, from that LGA's WeatherDays (any order)."""
    days = sorted((d for d in weather if today - timedelta(days=14) <= d.date <= today + timedelta(days=6)),
                  key=lambda d: d.date)
    if not days:
        return []
    source = days[-1].source
    past = [d for d in days if d.date < today]
    forecast = [d for d in days if d.date >= today]
    flood_window = [d for d in days if d.date >= today - timedelta(days=3)]
    out = []
    for hazard, result in (
        ("malaria", malaria_risk(past)),
        ("heat", heat_risk(forecast)),
        ("flood", flood_risk(flood_window)),
    ):
        if result is not None:
            score, level, explanation, inputs = result
            out.append(RiskAssessment(lga=lga, date=today, hazard=hazard, score=score, level=level,
                                      explanation=explanation, inputs=inputs, source=source))
    return out


def assess_lga(lga, today=None):
    today = today or date.today()
    results = []
    for ra in compute(lga, today, WeatherDay.objects.filter(lga=lga)):
        saved, _ = RiskAssessment.objects.update_or_create(
            lga=lga, date=today, hazard=ra.hazard,
            defaults={f: getattr(ra, f) for f in ("score", "level", "explanation", "inputs", "source")},
        )
        results.append(saved)
    return results


def assess_many(lgas, dates):
    """Score many LGAs for several days with one weather query and bulk writes."""
    lgas = list(lgas)
    weather = {}
    lo, hi = min(dates) - timedelta(days=14), max(dates) + timedelta(days=6)
    for d in WeatherDay.objects.filter(lga__in=lgas, date__gte=lo, date__lte=hi):
        weather.setdefault(d.lga_id, []).append(d)
    objs = [ra for lga in lgas for day in dates for ra in compute(lga, day, weather.get(lga.id, []))]
    RiskAssessment.objects.filter(lga__in=lgas, date__in=dates).delete()
    RiskAssessment.objects.bulk_create(objs, batch_size=1000)
    return len(objs)


def latest_risks(lga):
    """Most recent assessment per hazard for an LGA: {hazard: RiskAssessment}."""
    out = {}
    for ra in RiskAssessment.objects.filter(lga=lga).order_by("-date"):
        out.setdefault(ra.hazard, ra)
        if len(out) == 3:
            break
    return out
