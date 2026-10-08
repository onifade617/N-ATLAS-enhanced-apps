from django.contrib import admin

from .models import Immunization, Vaccine


@admin.register(Vaccine)
class VaccineAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "age_label", "age_days", "protects_against")


@admin.register(Immunization)
class ImmunizationAdmin(admin.ModelAdmin):
    list_display = ("child", "vaccine", "given_date", "facility")
    list_filter = ("vaccine",)
