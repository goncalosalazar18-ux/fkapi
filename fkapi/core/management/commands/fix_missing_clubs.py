from django.core.management.base import BaseCommand
from core.models import Club
from core.scrapers import scrape_club_details
from concurrent.futures import ThreadPoolExecutor

class Command(BaseCommand):
    help = 'Fix missing clubs'

    def handle(self, *args, **options):
        missing_clubs=set()
        with open('clubs_to_fix.txt', 'r', encoding='utf-8') as file:
            for line in file:
                slug=line.strip()
                missing_clubs.add(slug)
        for slug in missing_clubs:
            try:
                with ThreadPoolExecutor(max_workers=15) as executor:
                    executor.submit(scrape_club_details, slug)
            except Exception as e:
                print(f"Error: {e}")
        open('clubs_to_fix.txt', 'w').close()  # Remove all content from the file after processing
            

