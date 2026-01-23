from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from core.models import Club
from core.scrapers import scrape_club


class Command(BaseCommand):
    help = "Scrapes club data from the web"

    def handle(self, *args, **options):
        # Multithreading 15 workers to scrape all clubs
        clubs = Club.objects.filter(logo__isnull=True)
        with ThreadPoolExecutor(max_workers=15) as executor:
            for club in clubs:
                executor.submit(scrape_club, club.slug, True)
