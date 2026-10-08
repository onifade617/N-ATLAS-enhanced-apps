from django.db import models

from core.models import Child, Facility, Profile


class Vaccine(models.Model):
    code = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=80)
    protects_against = models.CharField(max_length=150)
    age_days = models.PositiveIntegerField(help_text="Recommended age in days on the routine schedule")
    age_label = models.CharField(max_length=20)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["age_days", "sort_order"]

    def __str__(self):
        return self.name


class Immunization(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="immunizations")
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE)
    given_date = models.DateField()
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("child", "vaccine")
        ordering = ["given_date"]

    def __str__(self):
        return f"{self.child} — {self.vaccine} on {self.given_date}"
