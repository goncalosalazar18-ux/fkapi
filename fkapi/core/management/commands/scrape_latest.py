from core.models import Brand, Competition, Club, Kit
from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.scrapers import scrape_latest_pages
import time
from colorama import Fore
import os

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
            '--retry-failed',
            action='store_true',
            help='Retry scraping clubs that previously failed'
        )

    def handle(self, *args, **options):
        start_page = options['start_page']
        end_page = options['end_page']
        retry_failed = options['retry_failed']

        # If retrying failed clubs
        if retry_failed:
            self.retry_failed_clubs()
            return

        # Normal scraping process
        print(Fore.CYAN + f"Starting scrape from page {start_page} to {end_page}")
        
        # First fix any missing clubs
        print(Fore.CYAN + "Fixing missing clubs...")
        call_command('fix_missing_clubs')
        
        # Then scrape latest pages
        print(Fore.CYAN + "Scraping latest pages...")
        success, failure = scrape_latest_pages(
            page_start=start_page,
            page_end=end_page,
            use_proxy=True,
            delay=2  # Add a small delay between pages
        )
        
        print(Fore.GREEN + f"\nScraping completed!")
        print(f"Successfully scraped pages: {success}")
        print(f"Failed pages: {failure}")
        
        if os.path.exists('clubs_to_fix.txt'):
            with open('clubs_to_fix.txt', 'r') as f:
                failed_clubs = len(f.readlines())
            print(Fore.YELLOW + f"\nFailed clubs logged: {failed_clubs}")
            print("Run 'python manage.py scrape_latest --retry-failed' to retry failed clubs")

    def retry_failed_clubs(self):
        """Retry scraping clubs that previously failed."""
        if not os.path.exists('clubs_to_fix.txt'):
            print(Fore.YELLOW + "No failed clubs to retry")
            return

        print(Fore.CYAN + "Retrying failed clubs...")
        
        # Read failed clubs
        with open('clubs_to_fix.txt', 'r') as f:
            failed_clubs = [line.strip().split(' - ')[0] for line in f.readlines()]
        
        # Create new file for clubs that fail again
        temp_file = 'clubs_to_fix_temp.txt'
        success_count = 0
        
        for club_slug in failed_clubs:
            print(Fore.CYAN + f"\nRetrying {club_slug}")
            try:
                # Try to scrape club again with increased timeout and retries
                club = Club.objects.get(slug=club_slug)
                if club.scrape_details(use_proxy=True, max_retries=5, timeout=30):
                    success_count += 1
                    print(Fore.GREEN + f"Successfully scraped {club_slug}")
                else:
                    print(Fore.RED + f"Failed to scrape {club_slug}")
                    with open(temp_file, 'a') as f:
                        f.write(f"{club_slug} - Retry failed\n")
            except Exception as e:
                print(Fore.RED + f"Error retrying {club_slug}: {str(e)}")
                with open(temp_file, 'a') as f:
                    f.write(f"{club_slug} - {str(e)}\n")
            
            time.sleep(2)  # Delay between retries
        
        # Replace original file with new one
        if os.path.exists(temp_file):
            os.replace(temp_file, 'clubs_to_fix.txt')
        
        print(Fore.GREEN + f"\nRetry completed!")
        print(f"Successfully recovered: {success_count}")
        print(f"Still failed: {len(failed_clubs) - success_count}")

