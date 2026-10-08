from django.contrib import admin

from .models import Conversation, Message, Referral, WhatsAppContact


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("role", "text", "intent", "emergency", "generated_by")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("profile", "started_at")
    inlines = [MessageInline]


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("profile", "facility", "service", "urgency", "status", "created_at")
    list_filter = ("status", "urgency", "service")


@admin.register(WhatsAppContact)
class WhatsAppContactAdmin(admin.ModelAdmin):
    list_display = ("phone", "display_name", "language", "state", "profile", "updated_at")
    list_filter = ("state", "language")
