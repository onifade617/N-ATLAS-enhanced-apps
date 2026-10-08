from django.contrib import admin
from django.urls import include, path

from navigator.views import twilio_whatsapp, voice_file

admin.site.site_header = "Lafiya AI administration"
admin.site.site_title = "Lafiya AI"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("mamacare/", include("mamacare.urls")),
    path("immunitrack/", include("immunitrack.urls")),
    path("climate/", include("climateguard.urls")),
    path("alerts/", include("alerts.urls")),
    path("navigator/", include("navigator.urls")),
    path("whatsapp/twilio/", twilio_whatsapp, name="twilio_whatsapp"),
    path("voice/<uuid:clip_id>.<str:ext>", voice_file, name="voice_file"),
    path("", include("dashboard.urls")),
]
