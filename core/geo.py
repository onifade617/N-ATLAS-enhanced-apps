"""Facility finder helpers."""

import math

from .models import Facility


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Search windows in degrees (~11, 28, 67, 167 km). None = whole country.
SEARCH_WINDOWS = (0.1, 0.25, 0.6, 1.5, None)
KM_PER_DEGREE = 108  # conservative for Nigeria's latitudes (4°–14° N)


def nearest_facilities(origin, service=None, limit=5, open_now_only=False, max_km=None):
    """Return [(facility, distance_km)] sorted by distance from origin (lat, lon).

    Searches a growing bounding box (indexed lat/lon) so it stays fast with ~55,000 facilities,
    and only accepts results inside the box's inscribed radius, so the answer is the true nearest.
    """
    if not origin:
        return []
    lat, lon = origin
    base = Facility.objects.select_related("lga", "lga__state")
    if service:
        base = base.filter(services__contains=service)
    for window in SEARCH_WINDOWS:
        qs = base
        if window is not None:
            qs = qs.filter(latitude__range=(lat - window, lat + window), longitude__range=(lon - window, lon + window))
        radius = window * KM_PER_DEGREE if window is not None else float("inf")
        results = []
        for f in qs:
            if service and not f.offers(service):  # guard against substring matches
                continue
            if open_now_only and not f.open_now:
                continue
            d = haversine_km(lat, lon, f.latitude, f.longitude)
            if d > radius or (max_km is not None and d > max_km):
                continue
            results.append((f, round(d, 1)))
        if len(results) >= limit or window is None or (max_km is not None and radius >= max_km):
            results.sort(key=lambda x: x[1])
            return results[:limit]
    return []


def best_facility(origin, service=None):
    """Nearest facility for a service, preferring one that is open now."""
    candidates = nearest_facilities(origin, service=service, limit=5)
    if not candidates:
        return None
    nearest = candidates[0]
    for f, d in candidates:
        if f.open_now and d <= nearest[1] + 5:
            return f, d
    return nearest


def facility_payload(facility, distance=None):
    return {
        "id": facility.id,
        "name": facility.name,
        "type": facility.get_facility_type_display(),
        "lga": facility.lga.name,
        "distance_km": distance,
        "open_now": facility.open_now,
        "hours": facility.opening_summary,
        "hours_verified": facility.hours_verified,
        "hours_text": facility.hours_text,
        "ownership": facility.ownership,
        "registry_code": facility.registry_code,
        "source": facility.source,
        "phone": facility.phone,
        "services": facility.service_labels,
        "lat": facility.latitude,
        "lon": facility.longitude,
        "map_url": f"https://www.openstreetmap.org/?mlat={facility.latitude}&mlon={facility.longitude}#map=16/{facility.latitude}/{facility.longitude}",
    }
