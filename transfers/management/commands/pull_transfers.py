from django.core.management.base import BaseCommand

from transfers.core_client import fetch_ready_transfers


class Command(BaseCommand):
    help = "Holt neue, freigegebene Transfers vom xfr-core ab."

    def handle(self, *args, **options):
        count = fetch_ready_transfers()
        self.stdout.write(self.style.SUCCESS(f"{count} neue Transfers abgeholt."))
