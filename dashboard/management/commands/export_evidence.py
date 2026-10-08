"""Export real-world validation evidence for the NAIC submission.

    python manage.py export_evidence                       # summary + anonymised CSV
    python manage.py export_evidence --with-text -o evidence.csv

--with-text includes the questions and replies. Users consented to storage for
service delivery; review the text (remove names/phone numbers) before sharing it.
"""

import json
import sys

from django.core.management.base import BaseCommand

from dashboard.evidence import summary, write_csv


class Command(BaseCommand):
    help = "Export anonymised real-user interaction evidence (excludes demo data)."

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", default="lafiya-evidence.csv")
        parser.add_argument("--with-text", action="store_true", help="Include question and reply text")

    def handle(self, *args, **opts):
        with open(opts["output"], "w", newline="", encoding="utf-8") as fh:
            write_csv(fh, with_text=opts["with_text"])
        s = summary()
        self.stdout.write(json.dumps(s, indent=2, ensure_ascii=True))
        status = "TARGET MET" if s["total"] >= s["target"] else f"{s['target'] - s['total']} to go"
        self.stdout.write(self.style.SUCCESS(f"{s['total']}/{s['target']} real interactions ({status}). "
                                             f"Wrote {opts['output']}"))
        if opts["with_text"]:
            sys.stderr.write("Note: the CSV contains message text - review it before sharing.\n")
