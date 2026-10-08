"""Real-world validation evidence (NAIC PS02: ≥50 documented real user interactions).

Only real users count: demo/synthetic profiles (is_demo=True) are excluded. Users are
pseudonymised with a salted hash; question/answer text is exported only on request.
"""

import csv
import hashlib
import statistics
from collections import Counter

from django.conf import settings

from core.models import LANGUAGE_NAMES
from navigator.models import Message

TARGET = 50
FIELDS = [
    "interaction_id", "timestamp", "user_ref", "channel", "input_mode", "asr_engine", "language", "intent",
    "emergency", "reply_generated_by", "latency_ms", "facility_suggested", "referral_created", "reminder_booked",
]
TEXT_FIELDS = ["question", "reply"]


def user_ref(profile_id):
    return hashlib.sha256(f"{settings.SECRET_KEY}:{profile_id}".encode()).hexdigest()[:10]


def interactions():
    """Yield (question_message, reply_message) pairs from real (non-demo) users, oldest first."""
    replies = (
        Message.objects.filter(role="assistant", conversation__profile__is_demo=False)
        .select_related("conversation")
        .order_by("created_at", "id")
    )
    for reply in replies:
        question = (
            Message.objects.filter(conversation=reply.conversation, role="user", id__lt=reply.id).order_by("-id").first()
        )
        if question:
            yield question, reply


def rows(with_text=False):
    for q, a in interactions():
        p = a.payload or {}
        row = {
            "interaction_id": a.id,
            "timestamp": a.created_at.isoformat(timespec="seconds"),
            "user_ref": user_ref(a.conversation.profile_id),
            "channel": a.channel,
            "input_mode": q.input_mode,
            "asr_engine": q.asr_engine,
            "language": a.language,
            "intent": a.intent,
            "emergency": a.emergency,
            "reply_generated_by": a.generated_by,
            "latency_ms": a.latency_ms,
            "facility_suggested": bool(p.get("facilities")),
            "referral_created": bool(p.get("referral_id")),
            "reminder_booked": bool(p.get("reminder")),
        }
        if with_text:
            row.update(question=q.text, reply=a.text)
        yield row


def write_csv(fh, with_text=False):
    writer = csv.DictWriter(fh, fieldnames=FIELDS + (TEXT_FIELDS if with_text else []))
    writer.writeheader()
    for row in rows(with_text):
        writer.writerow(row)


def summary():
    data = list(rows())
    voice = [r for r in data if r["input_mode"] == "voice"]
    latencies = [r["latency_ms"] for r in data if r["latency_ms"] is not None]
    return {
        "target": TARGET,
        "total": len(data),
        "progress": min(100, round(100 * len(data) / TARGET)),
        "users": len({r["user_ref"] for r in data}),
        "voice": len(voice),
        "voice_natlas_asr": sum(1 for r in voice if r["asr_engine"] == "n-atlas"),
        "replies_natlas": sum(1 for r in data if r["reply_generated_by"] == "n-atlas"),
        "by_channel": Counter(r["channel"] for r in data).most_common(),
        "by_language": [(LANGUAGE_NAMES.get(k, k), v) for k, v in Counter(r["language"] for r in data).most_common()],
        "top_intents": Counter(r["intent"] for r in data).most_common(6),
        "emergencies": sum(1 for r in data if r["emergency"]),
        "referrals": sum(1 for r in data if r["referral_created"]),
        "reminders": sum(1 for r in data if r["reminder_booked"]),
        "median_latency_ms": int(statistics.median(latencies)) if latencies else None,
        "first": data[0]["timestamp"] if data else None,
        "last": data[-1]["timestamp"] if data else None,
    }
