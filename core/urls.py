from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("home/", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/setup/", views.profile_setup, name="profile_setup"),
    path("profile/export/", views.export_my_data, name="export_my_data"),
    path("profile/delete/", views.delete_my_data, name="delete_my_data"),
    path("facilities/", views.facility_finder, name="facilities"),
]
