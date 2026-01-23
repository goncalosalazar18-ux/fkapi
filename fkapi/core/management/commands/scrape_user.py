import time

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from core.http import http_get
from core.models import Kit
from core.scrapers import scrape_kit


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username to scrape")

    def handle(self, *args, **options):
        items = []
        username = options["username"]
        # keep scraping pages until no more pages
        for page in range(1, 100):
            response = http_get(
                f"https://www.footballkitarchive.com/user/{username}?p={page}",
            )
            print(f"Scraping page {page}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                for kit in soup.select("div.kit"):
                    a = kit.find("a")
                    if a:
                        items.append(a["href"])

                next_page_link = soup.select_one("div.pager a.button[href*='?p=']")
                if not next_page_link:
                    break

        for item in items:
            # Extract slug and kit_id from href (format: slug/id/ or slug/id)
            slug_parts = item.strip("/").split("/")
            clean_slug = slug_parts[0]
            kit_id = slug_parts[1] if len(slug_parts) > 1 else None

            # find if a kit objects with the slug exists
            kit = Kit.objects.filter(slug=clean_slug).first()
            if kit:
                print(f"Kit {kit.name} already exists")
            else:
                scrape_kit(clean_slug, kit_id=kit_id)
                time.sleep(1)
