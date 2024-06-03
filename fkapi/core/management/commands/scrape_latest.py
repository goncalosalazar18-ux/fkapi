from core.models import Brand, Competition, Club, Kit
from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.scrapers import scrape_latest_pages

class Command(BaseCommand):
    help = 'Scrapes the latest kits'

    def handle(self, *args, **options):
        # execute command to fix missing clubs fix_missing_clubs
        call_command('fix_missing_clubs')
        scrape_latest_pages(1,10)

