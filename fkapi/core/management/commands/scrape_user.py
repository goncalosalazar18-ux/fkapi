import json
import logging

from django.core.management.base import BaseCommand

from core.scrapers import scrape_user_collection_api

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scrape user collection from FootballKitArchive using user ID"

    def add_arguments(self, parser):
        parser.add_argument("userid", type=int, help="User ID to scrape (integer)")

    def handle(self, *args, **options):
        userid = options["userid"]

        self.stdout.write(self.style.SUCCESS(f"Starting to scrape collection for userid: {userid}"))

        try:
            # Configure logging to show INFO level
            logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
            logger.setLevel(logging.INFO)

            # Scrape collection using the API
            data = scrape_user_collection_api(userid)

            entries = data.get("entries", [])
            total_entries = len(entries)
            pages_scraped = data.get("pages_scraped", 0)

            self.stdout.write(
                self.style.SUCCESS(f"Successfully scraped {total_entries} entries from {pages_scraped} pages")
            )

            if total_entries == 0:
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️  WARNING: No entries returned. This could mean:\n"
                        "  1. All entries were filtered out (custom fields, purchase/value, gender/printing_type)\n"
                        "  2. The user has no collection items\n"
                        "  3. There was an issue with the API response\n"
                        "\nCheck the logs above for filtering details."
                    )
                )

            # Optionally, extract kit slugs and IDs for further processing
            kit_info = []
            for entry in entries:
                kit = entry.get("kit", {})
                kit_url = kit.get("url", "")
                if kit_url:
                    # Parse /slug/id/ format
                    kit_url = kit_url.strip("/")
                    parts = kit_url.split("/")
                    if len(parts) >= 2:
                        slug = parts[0]
                        kit_id = parts[1]
                        kit_info.append({"slug": slug, "kit_id": kit_id})

            if kit_info:
                self.stdout.write(f"\nExtracted {len(kit_info)} kit references:")
                for info in kit_info[:10]:  # Show first 10
                    self.stdout.write(f"  - {info['slug']} (ID: {info['kit_id']})")
                if len(kit_info) > 10:
                    self.stdout.write(f"  ... and {len(kit_info) - 10} more")

            # Optionally save to file for inspection
            output_file = f"user_collection_{userid}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.stdout.write(self.style.SUCCESS(f"\nData saved to: {output_file}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error scraping user collection: {str(e)}"))
            raise
