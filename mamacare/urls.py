from django.urls import path

from . import views

urlpatterns = [
    path("", views.overview, name="mamacare"),
    path("pregnancy/add/", views.add_pregnancy, name="mamacare_add_pregnancy"),
    path("pregnancy/<int:pk>/end/", views.end_pregnancy, name="mamacare_end_pregnancy"),
    path("visit/<int:pk>/toggle/", views.mark_visit, name="mamacare_mark_visit"),
]
