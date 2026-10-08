from django.urls import path

from . import views

urlpatterns = [
    path("", views.risk_view, name="climate"),
]
