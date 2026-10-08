from django.conf import settings

from .models import LANGUAGES


def lafiya(request):
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    unread = 0
    if profile is not None:
        unread = profile.alerts.filter(opened_at__isnull=True).count()
    return {
        "profile": profile,
        "unread_alerts": unread,
        "LANGUAGES": LANGUAGES,
        "natlas_live": bool(settings.NATLAS["API_URL"]),
        "challenge_mode": settings.CHALLENGE_MODE,
    }
