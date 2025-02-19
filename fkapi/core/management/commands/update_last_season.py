# Update photos from last season as some of them may had been leaked photos and now they are oficcial photos
#Season 2024-25 or 2024
from core.models import Kit,Season
from core.scrapers import scrape_kit
from colorama import Fore
from django.core.management.base import BaseCommand

import concurrent.futures
from django.core.management.base import BaseCommand
from core.models import Kit, Season
from core.scrapers import scrape_kit

from django.core.management.base import BaseCommand
import concurrent.futures
from core.models import Kit, Season
from core.scrapers import scrape_kit

from django.core.management.base import BaseCommand
import concurrent.futures
from datetime import datetime
from core.models import Kit, Season
from core.scrapers import scrape_kit
from colorama import Fore

class Command(BaseCommand):
    help = 'Updates kit photos from the current season (both YYYY and YYYY-YY formats)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            type=int,
            default=10,
            help='Number of worker threads (default: 10)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all kits regardless of last_updated'
        )

    def handle(self, *args, **options):
        # Get current year based on football season (July-June)
        current_month = datetime.now().month
        current_year = datetime.now().year
        season_year = current_year if current_month >= 7 else current_year - 1
        
        self.stdout.write(
            self.style.SUCCESS(f"Updating kits for season {season_year} and {season_year}-{str(season_year + 1)[2:]}")
        )

        # Get both season formats
        seasons = Season.objects.filter(
            first_year__in=[str(season_year)]
        ) | Season.objects.filter(
            year__in=[
                f"{season_year}",
                f"{season_year}-{str(season_year + 1)[2:]}"
            ]
        )

        if not seasons.exists():
            self.stdout.write(
                self.style.ERROR(f"No seasons found for year {season_year}")
            )
            return

        def update_kit(kit: Kit) -> tuple[bool, str]:
            """
            Updates a single kit.
            
            Returns:
                tuple[bool, str]: (success, message)
            """
            retries = 0
            while retries < 3:
                try:
                    result = scrape_kit(kit.slug, use_proxy=True)
                    if result:
                        return True, f"Successfully updated {kit.slug}"
                    retries += 1
                except Exception as e:
                    retries += 1
                    if retries == 3:
                        return False, f"Failed to update {kit.slug}: {str(e)}"

            return False, f"Failed to update {kit.slug} after 3 retries"

        success_count = 0
        error_count = 0
        workers = options['workers']
        force = options['force']

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures_to_kits = {}
            
            # Submit all kits for processing
            for season in seasons:
                kits = Kit.objects.filter(season=season)
                if not force:
                    # Only update kits that haven't been updated in the last week
                    kits = kits.filter(
                        last_updated__lt=datetime.now() - datetime.timedelta(days=7)
                    )
                
                self.stdout.write(
                    f"Found {kits.count()} kits to update for season {season}"
                )
                
                for kit in kits:
                    future = executor.submit(update_kit, kit)
                    futures_to_kits[future] = kit

            # Process results as they complete
            for future in concurrent.futures.as_completed(futures_to_kits):
                kit = futures_to_kits[future]
                try:
                    success, message = future.result()
                    if success:
                        success_count += 1
                        self.stdout.write(self.style.SUCCESS(message))
                    else:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(message))
                        # Log errors
                        with open('update_last_season_errors.log', 'a', encoding='utf-8') as log:
                            log.write(f"{datetime.now()}: {message}\n")
                except Exception as e:
                    error_count += 1
                    error_msg = f"Error processing {kit.slug}: {str(e)}"
                    self.stdout.write(self.style.ERROR(error_msg))
                    with open('update_last_season_errors.log', 'a', encoding='utf-8') as log:
                        log.write(f"{datetime.now()}: {error_msg}\n")

        # Print summary
        self.stdout.write("\nUpdate completed!")
        self.stdout.write(f"Successfully updated: {success_count} kits")
        self.stdout.write(f"Failed to update: {error_count} kits")
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING("Check update_last_season_errors.log for details on failures")
            )