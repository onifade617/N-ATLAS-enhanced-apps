from django.core.management.base import BaseCommand

from core.geography import load_geography


class Command(BaseCommand):
    help = "Load all 36 states + FCT and 774 LGAs (OCHA COD-AB) - safe to re-run."

    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS(str(load_geography())))
