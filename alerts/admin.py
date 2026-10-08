from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "profile", "kind", "language", "scheduled_for", "generated_by", "opened_at", "acted_on_at")
    list_filter = ("kind", "language", "generated_by")
    search_fields = ("title", "profile__full_name")
