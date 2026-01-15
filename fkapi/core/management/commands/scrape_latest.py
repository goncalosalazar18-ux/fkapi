import concurrent.futures
import os
import threading
import time

from colorama import Fore
from django.core.management.base import BaseCommand

from core.models import Club
from core.scrapers import scrape_lastest


class Command(BaseCommand):
    help = 'Scrapes the latest kits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-page',
            type=int,
            default=1,
            help='Page number to start scraping from'
        )
        parser.add_argument(
            '--end-page',
            type=int,
            default=300,
            help='Page number to end scraping at'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=4,
            help='Number of worker threads (default: 4)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=2,
            help='Delay in seconds between pages (default: 2)'
        )

    def handle(self, *args, **options):
        start_page = options['start_page']
        end_page = options['end_page']
        workers = options['workers']
        delay = options['delay']

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

        # Scrape latest pages with workers
        print(Fore.CYAN + "Scraping latest pages...")
        success, failure = self.scrape_with_workers(
            page_range=page_range,
            workers=workers,
            delay=delay,
            use_proxy=True
        )

        print(Fore.GREEN + "\nScraping completed!")
        print(f"Successfully scraped pages: {success}")
        print(f"Failed pages: {failure}")

    def scrape_with_workers(self, page_range, workers, delay, use_proxy):
        """Scrape pages using worker threads with progress tracking."""
        success_count = 0
        failure_count = 0
        processed_count = 0
        total_pages = len(page_range)

        # Thread-safe counters
        self.success_count = 0
        self.failure_count = 0
        self.processed_count = 0
        self.lock = threading.Lock()

        print(Fore.CYAN + f"Starting parallel scraping with {workers} workers...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all pages to workers
            futures_to_pages = {}
            for page in page_range:
                future = executor.submit(self.scrape_single_page, page, use_proxy, delay)
                futures_to_pages[future] = page

            # Process results as they complete
            for future in concurrent.futures.as_completed(futures_to_pages):
                page = futures_to_pages[future]
                processed_count += 1

                # Update progress
                progress = (processed_count / total_pages) * 100
                title = f"FKApi - Scraping ({processed_count}/{total_pages} - {progress:.1f}%)"
                os.system(f"title {title}")

                try:
                    success = future.result()
                    if success:
                        success_count += 1
                        print(Fore.GREEN + f"✓ Page {page} completed successfully")
                    else:
                        failure_count += 1
                        print(Fore.RED + f"✗ Page {page} failed")
                except Exception as e:
                    failure_count += 1
                    print(Fore.RED + f"✗ Page {page} error: {str(e)}")

        return success_count, failure_count

    def scrape_single_page(self, page, use_proxy, delay):
        """Scrape a single page with error handling."""
        try:
            print(Fore.CYAN + f"Processing page {page}...")
            success = scrape_lastest(page, use_proxy)

            # Add delay between pages
            if delay > 0:
                time.sleep(delay)

            return success
        except Exception as e:
            print(Fore.RED + f"Error scraping page {page}: {str(e)}")
            return False

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


