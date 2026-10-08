from django.contrib import admin

from .models import ANCVisit, DangerSign, Milestone, Pregnancy


class ANCVisitInline(admin.TabularInline):
    model = ANCVisit
    extra = 0


@admin.register(Pregnancy)
class PregnancyAdmin(admin.ModelAdmin):
    list_display = ("profile", "lmp_date", "edd", "active", "high_risk")
    list_filter = ("active", "high_risk")
    inlines = [ANCVisitInline]


admin.site.register(Milestone)


@admin.register(DangerSign)
class DangerSignAdmin(admin.ModelAdmin):
    list_display = ("sign", "category", "keywords")
    list_filter = ("category",)
