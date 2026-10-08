"""Check the connection to the N-ATLaS gateway: health, chat, and (optionally) speech-to-text.

    python manage.py natlas_check
    python manage.py natlas_check --audio sample.ogg --language ha
"""

import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from navigator import natlas


class Command(BaseCommand):
    help = "Test the N-ATLaS gateway connection (health, chat, optional transcription)."

    def add_arguments(self, parser):
        parser.add_argument("--audio", help="Path to a short voice note to transcribe")
        parser.add_argument("--language", default="ha", choices=["en", "ha", "ig", "yo", "pcm"])

    def handle(self, *args, **opts):
        if not natlas.is_configured():
            raise CommandError("NATLAS_BASE_URL is not set. Add it (and NATLAS_API_KEY) to .env.")
        self.stdout.write(f"Gateway: {natlas.endpoint('')}  model: {settings.NATLAS['MODEL']}")

        self.stdout.write("1. GET /health (a cold start can take several minutes)...")
        ok, details = natlas.health(timeout=max(30, settings.NATLAS["TIMEOUT"]))
        self.stdout.write(("   OK " if ok else "   NOT READY ") + json.dumps(details, ensure_ascii=True)[:400])

        self.stdout.write("2. POST /v1/chat/completions ...")
        reply = natlas.chat([{"role": "user", "content": "Sannu! Say hello in one short sentence."}], language="ha", max_tokens=40)
        if reply:
            self.stdout.write(self.style.SUCCESS("   OK " + reply.encode("ascii", "replace").decode()))
        else:
            self.stdout.write(self.style.ERROR("   FAILED - check NATLAS_API_KEY, or retry after the cold start (see log above)."))

        if opts["audio"]:
            path = Path(opts["audio"])
            self.stdout.write(f"3. POST /v1/audio/transcriptions ({path.name}, {opts['language']}) ...")
            text = natlas.transcribe(path.read_bytes(), path.name, mimetypes.guess_type(path.name)[0], opts["language"])
            if text:
                self.stdout.write(self.style.SUCCESS("   OK " + text.encode("ascii", "replace").decode()))
            else:
                self.stdout.write(self.style.ERROR("   FAILED"))
