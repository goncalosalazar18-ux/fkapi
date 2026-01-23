from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from core.models import Club
from core.scrapers import scrape_whole_club


class Command(BaseCommand):
    help = "Scrape whole club"

    def handle(self, *args, **options):
        # get unique clubs in kits
        clubs = Club.objects.all()
        with ThreadPoolExecutor(max_workers=25) as executor:
            executor.map(scrape_whole_club, clubs)
