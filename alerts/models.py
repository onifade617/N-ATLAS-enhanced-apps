from django.db import models
from django.utils import timezone

from core.models import LANGUAGES, Facility, Profile


class Alert(models.Model):
    KINDS = [
        ("malaria", "Malaria risk"),
        ("heat", "Heat risk"),
        ("flood", "Flood risk"),
        ("vaccine", "Vaccine reminder"),
        ("anc", "Antenatal reminder"),
        ("reminder", "Booked reminder"),
    ]
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="alerts")
    kind = models.CharField(max_length=10, choices=KINDS)
    title = models.CharField(max_length=150)
    message = models.TextField()
    language = models.CharField(max_length=3, choices=LANGUAGES, default="en")
    reason = models.TextField(blank=True, help_text="Why this alert was sent (explainable risk)")
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_for = models.DateField(default=timezone.localdate)
    channel = models.CharField(max_length=10, default="app")
    generated_by = models.CharField(max_length=10, default="template", help_text="n-atlas or template")
    dedupe_key = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    acted_on_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-scheduled_for", "-created_at"]
        unique_together = ("profile", "dedupe_key")

    def __str__(self):
        return f"{self.get_kind_display()} → {self.profile}"

    @property
    def is_climate(self):
        return self.kind in ("malaria", "heat", "flood")

    @property
    def icon(self):
        return {
            "malaria": "bug",
            "heat": "thermometer-sun",
            "flood": "water",
            "vaccine": "shield-plus",
            "anc": "heart-pulse",
            "reminder": "bell",
        }[self.kind]
