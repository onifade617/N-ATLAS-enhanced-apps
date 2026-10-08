from django.contrib import admin

from .models import RiskAssessment, WeatherDay


@admin.register(WeatherDay)
class WeatherDayAdmin(admin.ModelAdmin):
    list_display = ("lga", "date", "temp_max", "apparent_temp_max", "precipitation_mm", "humidity_mean", "source", "is_forecast")
    list_filter = ("source", "lga__state")


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ("lga", "date", "hazard", "level", "score", "source")
    list_filter = ("hazard", "level", "lga__state")
