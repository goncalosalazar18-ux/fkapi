import os

from colorama import Fore
from django.core.management.base import BaseCommand

from core.scrapers import scrape_latest_pages


class Command(BaseCommand):
    help = "Scrapes the latest kits"

    def add_arguments(self, parser):
        parser.add_argument("--start-page", type=int, default=1, help="Page number to start scraping from")
        parser.add_argument("--end-page", type=int, default=300, help="Page number to end scraping at")
        parser.add_argument("--workers", type=int, default=4, help="Number of worker threads (default: 4)")
        parser.add_argument("--delay", type=int, default=2, help="Delay in seconds between pages (default: 2)")

    def handle(self, *args, **options):
        start_page = options["start_page"]
        end_page = options["end_page"]
        workers = options["workers"]
        delay = options["delay"]

        # Determine direction and create page range
        if start_page <= end_page:
            # Forward scraping: start_page to end_page (e.g., 1 to 100)
            page_range = range(start_page, end_page + 1)
            direction = "forward"
        else:
            # Backward scraping: start_page down to end_page (e.g., 1000 to 1)
            page_range = range(start_page, end_page - 1, -1)
            direction = "backward"

        # Normal scraping process
        print(Fore.CYAN + f"Starting scrape from page {start_page} to {end_page} ({direction})")
        print(Fore.CYAN + f"Total pages to process: {len(page_range)}")
        print(Fore.CYAN + f"Using {workers} workers with {delay}s delay between pages")

        # Scrape latest pages sequentially (kits within each page are processed in parallel)
        print(Fore.CYAN + "Scraping latest pages...")
        success, failure = scrape_latest_pages(
            page_start=start_page, page_end=end_page, use_proxy=True, delay=delay, reverse_order=(start_page > end_page)
        )

        print(Fore.GREEN + "\nScraping completed!")
        print(f"Successfully scraped pages: {success}")
        print(f"Failed pages: {failure}")

    def update_progress(self, current_page, start_page, end_page):
        """Update the command prompt title with scraping progress."""
        # Calculate progress regardless of direction
        if start_page <= end_page:
            # Forward progress
            total_pages = end_page - start_page + 1
            progress = ((current_page - start_page + 1) / total_pages) * 100
        else:
            # Backward progress
            total_pages = start_page - end_page + 1
            progress = ((start_page - current_page + 1) / total_pages) * 100

        title = f"Scraping page {current_page}/{end_page} ({progress:.1f}%)"
        os.system(f"title {title}")
