from django.contrib import admin

from .models import LGA, Child, Facility, Profile, State, Ward


class LGAInline(admin.TabularInline):
    model = LGA
    extra = 0


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    inlines = [LGAInline]


@admin.register(LGA)
class LGAAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "latitude", "longitude", "population")
    list_filter = ("state",)
    search_fields = ("name",)


admin.site.register(Ward)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "facility_type", "lga", "services", "opening_summary", "phone")
    list_filter = ("facility_type", "lga__state")
    search_fields = ("name",)


class ChildInline(admin.TabularInline):
    model = Child
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "language", "lga", "consent_given", "created_at")
    list_filter = ("role", "language", "lga__state", "consent_given")
    search_fields = ("full_name", "phone")
    inlines = [ChildInline]


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("name", "sex", "date_of_birth", "caregiver")
    search_fields = ("name",)
