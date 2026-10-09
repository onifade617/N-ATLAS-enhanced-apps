"""Check the connection to the N-ATLaS gateway: health, chat, and (optionally) speech-to-text.

    python manage.py natlas_check
    python manage.py natlas_check --audio sample.ogg --language ha

Outside Django, the same checks are ``natlas-health health`` / ``chat`` / ``transcribe``.
"""

import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from natlas_health import NatlasError
from navigator import natlas


class Command(BaseCommand):
    help = "Test the N-ATLaS gateway connection (health, chat, optional transcription)."

    def add_arguments(self, parser):
        parser.add_argument("--audio", help="Path to a short voice note to transcribe")
        parser.add_argument("--language", default="ha", choices=["en", "ha", "ig", "yo", "pcm"])

    def ok(self, text):
        self.stdout.write(self.style.SUCCESS("   OK " + text.encode("ascii", "replace").decode()))

    def failed(self, exc, hint=""):
        self.stdout.write(self.style.ERROR(f"   FAILED {exc.__class__.__name__}: {exc}{hint}"))

    def handle(self, *args, **opts):
        if not natlas.is_configured():
            raise CommandError("NATLAS_BASE_URL is not set. Add it (and NATLAS_API_KEY) to .env.")
        client = natlas.client()
        self.stdout.write(f"Gateway: {client.base_url}  model: {client.model}")

        self.stdout.write("1. GET /health (a cold start can take several minutes)...")
        status = client.health(timeout=max(30, settings.NATLAS["TIMEOUT"]))
        self.stdout.write(("   OK " if status.ok else "   NOT READY ") + json.dumps(status.details, ensure_ascii=True)[:400])

        self.stdout.write("2. POST /v1/chat/completions ...")
        try:
            reply = client.chat("Sannu! Say hello in one short sentence.", language="ha", max_tokens=40)
            self.ok(f"{reply.text}  ({reply.latency_ms} ms)")
        except NatlasError as exc:
            self.failed(exc, " - check NATLAS_API_KEY, or retry after the cold start.")

        if opts["audio"]:
            path = Path(opts["audio"])
            self.stdout.write(f"3. POST /v1/audio/transcriptions ({path.name}, {opts['language']}) ...")
            try:
                result = client.transcribe(path.read_bytes(), path.name, mimetypes.guess_type(path.name)[0],
                                           opts["language"])
                self.ok(f"{result.text}  ({result.latency_ms} ms)")
            except NatlasError as exc:
                self.failed(exc)
