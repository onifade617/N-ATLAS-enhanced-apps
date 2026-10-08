from django.urls import path

from . import views

urlpatterns = [
    path("worker/", views.worker_dashboard, name="worker_dashboard"),
    path("worker/enrol/", views.worker_enrol, name="worker_enrol"),
    path("worker/child/<int:child_id>/vaccinate/", views.worker_vaccinate, name="worker_vaccinate"),
    path("worker/anc/<int:visit_id>/", views.worker_anc, name="worker_anc"),
    path("worker/pregnancy/<int:pregnancy_id>/flag/", views.worker_flag, name="worker_flag"),
    path("worker/referral/<int:referral_id>/done/", views.worker_referral_done, name="worker_referral_done"),
    path("gov/", views.gov_dashboard, name="gov_dashboard"),
    path("gov/export.csv", views.gov_export, name="gov_export"),
    path("gov/run-loop/", views.gov_run_loop, name="gov_run_loop"),
    path("gov/evidence.csv", views.gov_evidence_export, name="gov_evidence_export"),
    path("api/v1/", views.api_index, name="api_index"),
    path("api/v1/lgas/", views.api_lgas, name="api_lgas"),
    path("api/v1/facilities/", views.api_facilities, name="api_facilities"),
    path("api/v1/states/", views.api_states, name="api_states"),
]
