"""Load ~55,000 real health facilities (GRID3 / Nigeria Health Facility Registry). Safe to re-run.

    python manage.py load_facilities            # also replaces synthetic demo facilities
    python manage.py load_facilities --keep-demo
"""

from django.core.management.base import BaseCommand

from core.facilities_data import load_facilities


class Command(BaseCommand):
    help = "Load real Nigerian health facilities from core/data/nigeria_health_facilities.csv.gz"

    def add_arguments(self, parser):
        parser.add_argument("--keep-demo", action="store_true", help="Keep synthetic demo facilities")

    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS(str(load_facilities(replace_demo=not opts["keep_demo"]))))
