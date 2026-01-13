from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
from core.scrapers import scrape_kit
from core.models import Kit
from core.http import http_get
import time


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to scrape')

    def handle(self, *args, **options):
        items = []
        username = options['username']
        # keep scraping pages until no more pages
        for page in range(1, 100):
            response = http_get(
                f"https://www.footballkitarchive.com/user/{username}?p={page}",
            )
            print(f"Scraping page {page}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for kit in soup.select("div.kit"):
                    a = kit.find("a")
                    if a:
                        items.append(a['href'])

                next_page_link = soup.select_one(
                    "div.pager a.button[href*='?p=']")
                if not next_page_link:
                    break

        for item in items:
            # find if a kit objects with the slug exists
            kit = Kit.objects.filter(slug=item.replace("/", "")).first()
            if kit:
                print(f"Kit {kit.name} already exists")
            else:
                scrape_kit(item)
                time.sleep(1)
