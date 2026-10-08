"""Weather ingestion: Open-Meteo (live) with a labelled seasonal simulation fallback."""

import json
import logging
import math
import random
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import date, timedelta

from django.conf import settings

from .models import WeatherDay

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "precipitation_sum",
    "relative_humidity_2m_mean",
]


BATCH_SIZE = 50  # Open-Meteo accepts comma-separated coordinate lists
RATE_LIMIT_WAIT = 61
RATE_LIMIT_RETRIES = 2


def fetch_open_meteo_batch(lgas, past_days=21, forecast_days=7):
    """One request for many LGAs. Returns {lga.id: rows}."""
    params = {
        "latitude": ",".join(f"{l.latitude:.4f}" for l in lgas),
        "longitude": ",".join(f"{l.longitude:.4f}" for l in lgas),
        "daily": ",".join(DAILY_VARS),
        "past_days": past_days,
        "forecast_days": forecast_days,
        "timezone": "Africa/Lagos",
    }
    url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                payload = json.load(resp)
            break
        except urllib.error.HTTPError as exc:
            # Free tier: ~600 location-calls per minute. A full national run (774 LGAs) can hit it.
            if exc.code != 429 or attempt == RATE_LIMIT_RETRIES:
                raise
            log.info("Open-Meteo rate limit reached; waiting %ss", RATE_LIMIT_WAIT)
            time.sleep(RATE_LIMIT_WAIT)
    payload = payload if isinstance(payload, list) else [payload]
    if len(payload) != len(lgas):
        raise ValueError(f"expected {len(lgas)} locations, got {len(payload)}")
    return {lga.id: _parse_daily(item["daily"]) for lga, item in zip(lgas, payload)}


def fetch_open_meteo(lga, past_days=21, forecast_days=7):
    return fetch_open_meteo_batch([lga], past_days, forecast_days)[lga.id]


def _parse_daily(data):
    rows = []
    for i, day in enumerate(data["time"]):
        values = [data[v][i] for v in DAILY_VARS]
        if any(v is None for v in values):
            continue
        rows.append(
            {
                "date": date.fromisoformat(day),
                "temp_max": values[0],
                "temp_min": values[1],
                "apparent_temp_max": values[2],
                "precipitation_mm": values[3],
                "humidity_mean": values[4],
            }
        )
    return rows


def simulate(lga, start, end):
    """Deterministic, climatology-shaped weather so the demo works offline.

    The north (higher latitude) is hotter and drier with a shorter rainy season
    (Jun–Sep); the south is wetter with a longer season (Apr–Oct).
    """
    rows = []
    north = min(1.0, max(0.0, (lga.latitude - 5) / 8))  # 0 = coast, 1 = far north
    d = start
    while d <= end:
        rng = random.Random(f"{lga.id}-{d.isoformat()}")
        doy = d.timetuple().tm_yday
        wet_centre = 225  # mid-August
        wet_width = 70 - 25 * north
        wetness = math.exp(-(((doy - wet_centre) / wet_width) ** 2))
        hot_season = math.exp(-(((doy - 100) / 45) ** 2))  # April peak
        tmax = 30 + 6 * north * hot_season + 3 * hot_season - 3 * wetness + rng.uniform(-1.5, 1.5)
        tmin = tmax - 8 - 4 * north * (1 - wetness) + rng.uniform(-1, 1)
        humidity = 45 + 40 * wetness + 15 * (1 - north) + rng.uniform(-5, 5)
        rain = 0.0
        if rng.random() < 0.15 + 0.65 * wetness:
            rain = rng.expovariate(1 / (6 + 18 * wetness * (1.2 - 0.4 * north)))
        apparent = tmax + max(0, (humidity - 40) / 10) * 1.2
        rows.append(
            {
                "date": d,
                "temp_max": round(tmax, 1),
                "temp_min": round(tmin, 1),
                "apparent_temp_max": round(apparent, 1),
                "precipitation_mm": round(rain, 1),
                "humidity_mean": round(min(98, max(15, humidity)), 0),
            }
        )
        d += timedelta(days=1)
    return rows


def ingest_lgas(lgas, today=None, live=None):
    """Store 21 past + 7 forecast days for many LGAs, batching API calls and DB writes.

    Returns {source: number_of_lgas}.
    """
    today = today or date.today()
    live = settings.CLIMATE_LIVE_WEATHER if live is None else live
    lgas = list(lgas)
    sources = {}
    for i in range(0, len(lgas), BATCH_SIZE):
        batch = lgas[i : i + BATCH_SIZE]
        fetched, source = {}, "simulated"
        if live:
            try:
                fetched, source = fetch_open_meteo_batch(batch), "open-meteo"
            except Exception as exc:
                log.warning("Open-Meteo batch failed (%s); using simulation for %d LGAs", exc, len(batch))
        objs = []
        for lga in batch:
            rows = fetched.get(lga.id) or simulate(lga, today - timedelta(days=21), today + timedelta(days=6))
            src = source if fetched.get(lga.id) else "simulated"
            sources[src] = sources.get(src, 0) + 1
            for row in rows:
                day = row.pop("date")
                objs.append(WeatherDay(lga=lga, date=day, is_forecast=day > today, source=src, **row))
        days = {o.date for o in objs}
        WeatherDay.objects.filter(lga__in=batch, date__in=days).delete()
        WeatherDay.objects.bulk_create(objs, batch_size=1000)
    return sources


def ingest_lga(lga, today=None, live=None):
    """Store 21 past days + 7 forecast days for one LGA. Returns the source used."""
    today = today or date.today()
    live = settings.CLIMATE_LIVE_WEATHER if live is None else live
    source = "simulated"
    rows = None
    if live:
        try:
            rows = fetch_open_meteo(lga)
            source = "open-meteo"
        except Exception as exc:  # network, quota, parse errors
            log.warning("Open-Meteo failed for %s (%s); using simulation", lga, exc)
    if not rows:
        rows = simulate(lga, today - timedelta(days=21), today + timedelta(days=6))
    for row in rows:
        day = row.pop("date")
        WeatherDay.objects.update_or_create(
            lga=lga, date=day, defaults={**row, "is_forecast": day > today, "source": source}
        )
    return source
