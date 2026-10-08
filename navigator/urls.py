from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat, name="navigator"),
    path("api/ask/", views.api_ask, name="navigator_ask"),
    path("api/refer/", views.accept_referral, name="navigator_refer"),
    path("api/transcribe/", views.api_transcribe, name="navigator_transcribe"),
    path("api/speak/", views.api_speak, name="navigator_speak"),
]
