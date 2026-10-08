from django.db import models

from core.models import LGA

HAZARDS = [("malaria", "Malaria"), ("heat", "Heat"), ("flood", "Flood")]
LEVELS = [("low", "Low"), ("moderate", "Moderate"), ("high", "High"), ("very_high", "Very high")]
LEVEL_ORDER = {"low": 0, "moderate": 1, "high": 2, "very_high": 3}


class WeatherDay(models.Model):
    lga = models.ForeignKey(LGA, on_delete=models.CASCADE, related_name="weather")
    date = models.DateField()
    temp_max = models.FloatField()
    temp_min = models.FloatField()
    apparent_temp_max = models.FloatField()
    precipitation_mm = models.FloatField()
    humidity_mean = models.FloatField()
    is_forecast = models.BooleanField(default=False)
    source = models.CharField(max_length=20, default="open-meteo")
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("lga", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.lga.name} {self.date}"


class RiskAssessment(models.Model):
    lga = models.ForeignKey(LGA, on_delete=models.CASCADE, related_name="risks")
    date = models.DateField()
    hazard = models.CharField(max_length=10, choices=HAZARDS)
    score = models.PositiveSmallIntegerField()
    level = models.CharField(max_length=10, choices=LEVELS)
    explanation = models.TextField(help_text="Plain-language reason: every alert says why")
    inputs = models.JSONField(default=dict)
    source = models.CharField(max_length=20, default="open-meteo")
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("lga", "date", "hazard")
        ordering = ["-date", "hazard"]

    def __str__(self):
        return f"{self.lga.name} {self.hazard} {self.level} ({self.date})"

    @property
    def is_elevated(self):
        return LEVEL_ORDER[self.level] >= LEVEL_ORDER["high"]

    def previous(self):
        return (
            RiskAssessment.objects.filter(lga=self.lga, hazard=self.hazard, date__lt=self.date)
            .order_by("-date")
            .first()
        )

    @property
    def trend(self):
        prev = self.previous()
        if prev is None:
            return "new"
        if self.score >= prev.score + 5:
            return "rising"
        if self.score <= prev.score - 5:
            return "falling"
        return "steady"
