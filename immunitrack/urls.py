from django.urls import path

from . import views

urlpatterns = [
    path("", views.overview, name="immunitrack"),
    path("child/add/", views.add_child, name="immunitrack_add_child"),
    path("child/<int:pk>/", views.child_detail, name="immunitrack_child"),
    path("child/<int:pk>/record/", views.record_vaccine, name="immunitrack_record"),
]
