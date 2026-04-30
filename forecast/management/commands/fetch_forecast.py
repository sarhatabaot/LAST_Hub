from django.conf import settings
from django.core.management.base import BaseCommand

from forecast import ingest


class Command(BaseCommand):
    help = "Download IMS forecast files and rebuild the local forecast cache."

    def handle(self, *args, **options):
        if not settings.IMS_USERNAME or not settings.IMS_PASSWORD:
            self.stdout.write(
                self.style.WARNING(
                    "IMS_USERNAME / IMS_PASSWORD are not set; skipping forecast fetch."
                )
            )
            return

        payload = ingest.run(
            username=settings.IMS_USERNAME,
            password=settings.IMS_PASSWORD,
            base_url=settings.IMS_BASE_URL,
            directory=settings.IMS_DIRECTORY,
            data_dir=settings.IMS_DATA_DIR,
            cache_path=settings.FORECAST_CACHE_PATH,
            location=(settings.OBS_LATITUDE, settings.OBS_LONGITUDE),
            verify_ssl=settings.IMS_VERIFY_SSL,
            retention_days=settings.FORECAST_RETENTION_DAYS,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Forecast cache updated with {len(payload)} series at {settings.FORECAST_CACHE_PATH}."
            )
        )
