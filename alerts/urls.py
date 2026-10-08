from django.urls import path

from . import views

urlpatterns = [
    path("", views.inbox, name="alerts"),
    path("<int:pk>/opened/", views.mark_opened, name="alert_opened"),
    path("<int:pk>/acted/", views.mark_acted, name="alert_acted"),
]
