import uuid

from django.db import models
from django.utils import timezone

from core.models import LANGUAGES, SERVICES, Facility, Profile


CHANNELS = [("web", "Web app"), ("whatsapp", "WhatsApp")]


class Conversation(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="conversations")
    channel = models.CharField(max_length=10, choices=CHANNELS, default="web")
    started_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-started_at"]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=[("user", "User"), ("assistant", "Lafiya")])
    text = models.TextField()
    language = models.CharField(max_length=3, choices=LANGUAGES, default="en")
    intent = models.CharField(max_length=20, blank=True)
    emergency = models.BooleanField(default=False)
    generated_by = models.CharField(max_length=10, blank=True)
    # Validation evidence (NAIC PS02): how the question arrived and how fast Lafiya answered.
    channel = models.CharField(max_length=10, choices=CHANNELS, default="web")
    input_mode = models.CharField(max_length=5, choices=[("text", "Text"), ("voice", "Voice")], default="text")
    asr_engine = models.CharField(max_length=10, blank=True, help_text="n-atlas or browser (voice input only)")
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]


class WhatsAppContact(models.Model):
    """Onboarding state for a WhatsApp number (language → consent → location → ready)."""

    STATES = [("language", "Choosing language"), ("consent", "Awaiting consent"), ("location", "Awaiting location"),
              ("ready", "Ready")]
    phone = models.CharField(max_length=20, unique=True, help_text="E.164, e.g. +2348012345678")
    display_name = models.CharField(max_length=80, blank=True)
    language = models.CharField(max_length=3, choices=LANGUAGES, default="en")
    state = models.CharField(max_length=10, choices=STATES, default="language")
    profile = models.OneToOneField(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="whatsapp")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone} ({self.state})"


class Referral(models.Model):
    URGENCY = [("routine", "Routine"), ("urgent", "Today"), ("emergency", "Emergency")]
    STATUS = [
        ("suggested", "Suggested"),
        ("accepted", "Accepted by user"),
        ("completed", "Completed at facility"),
        ("cancelled", "Cancelled"),
    ]
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="referrals")
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name="referrals")
    service = models.CharField(max_length=15, choices=SERVICES, blank=True)
    reason = models.CharField(max_length=200)
    urgency = models.CharField(max_length=10, choices=URGENCY, default="routine")
    status = models.CharField(max_length=10, choices=STATUS, default="suggested")
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.profile} → {self.facility} ({self.status})"


class VoiceClip(models.Model):
    """A spoken reply rendered by the N-ATLaS gateway (MMS-TTS). Served at an unguessable URL so
    Twilio can fetch it for WhatsApp; no personal data in the URL."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True, related_name="voice_clips")
    language = models.CharField(max_length=3, choices=LANGUAGES, default="en")
    voice = models.CharField(max_length=80, blank=True)
    audio = models.BinaryField()
    content_type = models.CharField(max_length=20, default="audio/mpeg")
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def extension(self):
        return "mp3" if self.content_type == "audio/mpeg" else "wav"
