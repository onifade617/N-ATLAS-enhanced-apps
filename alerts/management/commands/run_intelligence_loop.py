"""Daily job: Sense → Match → Speak → Act. Schedule with cron / Task Scheduler."""

from datetime import date

from django.core.management.base import BaseCommand

from alerts.engine import run_loop


class Command(BaseCommand):
    help = "Ingest weather, score climate-health risk per LGA and send personalised alerts and reminders."

    def add_arguments(self, parser):
        parser.add_argument("--offline", action="store_true", help="Use simulated weather")
        parser.add_argument("--no-weather", action="store_true", help="Skip weather refresh")
        parser.add_argument("--natlas", action="store_true", help="Let N-ATLaS write the alerts (uses GPU credit)")
        parser.add_argument("--no-natlas", action="store_true", help="Use templates even if LAFIYA_NATLAS_FOR_ALERTS=1")
        parser.add_argument("--max-natlas", type=int, default=50, help="Cap on N-ATLAS generations per run")
        parser.add_argument("--date", type=date.fromisoformat, default=None)

    def handle(self, *args, **opts):
        summary = run_loop(
            today=opts["date"],
            refresh_weather=not opts["no_weather"],
            live=False if opts["offline"] else None,
            use_natlas=True if opts["natlas"] else (False if opts["no_natlas"] else None),
            max_natlas=opts["max_natlas"],
        )
        self.stdout.write(self.style.SUCCESS(str(summary)))
