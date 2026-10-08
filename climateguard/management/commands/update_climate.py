from django.core.management.base import BaseCommand

from alerts.engine import sense


class Command(BaseCommand):
    help = "Refresh weather and climate-health risk scores for every LGA (no alerts)."

    def add_arguments(self, parser):
        parser.add_argument("--offline", action="store_true", help="Use simulated weather")

    def handle(self, *args, **opts):
        sources = sense(live=False if opts["offline"] else None)
        self.stdout.write(self.style.SUCCESS(f"Updated climate risk. Weather sources: {sources}"))
