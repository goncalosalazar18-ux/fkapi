# Update photos from last season as some of them may had been leaked photos and now they are oficcial photos
# Season 2024-25 or 2024
import concurrent.futures
import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Kit, Season
from core.scrapers import scrape_kit


class Command(BaseCommand):
    help = "Updates kit photos from the current season (both YYYY and YYYY-YY formats)"

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=10, help="Number of worker threads (default: 10)")
        parser.add_argument("--force", action="store_true", help="Force update all kits regardless of last_updated")

    def handle(self, *args, **options):
        # Force update specific seasons: 2026, 2025, 2025-26
        target_seasons = ["2026", "2025", "2025-26"]

        self.stdout.write(self.style.SUCCESS(f"Updating kits for seasons: {', '.join(target_seasons)}"))

        # Get both season formats
        seasons = Season.objects.filter(first_year__in=target_seasons) | Season.objects.filter(year__in=target_seasons)

        if not seasons.exists():
            self.stdout.write(self.style.ERROR(f"No seasons found for: {', '.join(target_seasons)}"))
            return

        def update_kit(kit: Kit) -> tuple[bool, str, str]:
            """
            Updates a single kit.

            Returns:
                tuple[bool, str, str]: (success, message, error_type)
                error_type can be: 'success', 'moved', 'network', 'other'
            """
            retries = 0
            while retries < 5:
                try:
                    result = scrape_kit(kit.slug, use_proxy=True)
                    if result:
                        # Check if the result has a different slug (new URL format)
                        if hasattr(result, "slug") and result.slug != kit.slug:
                            return True, f"Successfully updated {kit.slug} -> {result.slug}", "success"
                        else:
                            return True, f"Successfully updated {kit.slug}", "success"
                    else:
                        # Kit was not found - could be moved or network issue
                        # The scrape_kit function will have logged the specific reason
                        return False, f"Kit {kit.slug} not found", "moved"
                    retries += 1
                except Exception as e:
                    retries += 1
                    if retries == 3:
                        # Check if it's a network-related error
                        if "Network error" in str(e) or "timeout" in str(e).lower():
                            return False, f"Network error updating {kit.slug}: {str(e)}", "network"
                        else:
                            return False, f"Failed to update {kit.slug}: {str(e)}", "other"

            return False, f"Failed to update {kit.slug} after 3 retries", "other"

        success_count = 0
        error_count = 0
        not_found_count = 0
        network_error_count = 0
        workers = options["workers"]
        force = options["force"]

        # Get total kit count for progress tracking
        total_kits = 0
        for season in seasons:
            kits = Kit.objects.filter(season=season)
            if not force:
                kits = kits.filter(last_updated__lt=timezone.now() - timedelta(days=7))
            total_kits += kits.count()

        self.stdout.write(self.style.SUCCESS(f"Total kits to process: {total_kits}"))

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures_to_kits = {}
            processed_count = 0

            # Submit all kits for processing
            for season in seasons:
                kits = Kit.objects.filter(season=season)
                if not force:
                    # Only update kits that haven't been updated in the last week
                    kits = kits.filter(last_updated__lt=timezone.now() - timedelta(days=7))

                # Order by oldest kits first (those that haven't been updated the longest)
                kits = kits.order_by("last_updated")

                self.stdout.write(f"Found {kits.count()} kits to update for season {season}")

                for kit in kits:
                    future = executor.submit(update_kit, kit)
                    futures_to_kits[future] = kit

            # Process results as they complete
            for future in concurrent.futures.as_completed(futures_to_kits):
                kit = futures_to_kits[future]
                processed_count += 1

                # Update progress in title
                progress = (processed_count / total_kits) * 100
                title = f"FKApi - Update Last Season ({processed_count}/{total_kits} - {progress:.1f}%)"
                os.system(f"title {title}")

                try:
                    success, message, error_type = future.result()
                    if success:
                        success_count += 1
                        self.stdout.write(self.style.SUCCESS(message))
                    else:
                        if error_type == "moved":
                            not_found_count += 1
                            self.stdout.write(
                                self.style.WARNING(f"PAGE MOVED: {kit.slug} - checking for duplicates...")
                            )

                            # Check for potential duplicates and remove this kit
                            self._handle_moved_kit(kit)
                        elif error_type == "network":
                            network_error_count += 1
                            self.stdout.write(self.style.ERROR(f"NETWORK ERROR: {message}"))
                        else:
                            error_count += 1
                            self.stdout.write(self.style.ERROR(message))

                        # Log errors
                        with open("update_last_season_errors.log", "a", encoding="utf-8") as log:
                            log.write(f"{timezone.now()}: [{error_type.upper()}] {message}\n")
                except Exception as e:
                    error_count += 1
                    error_msg = f"Error processing {kit.slug}: {str(e)}"
                    self.stdout.write(self.style.ERROR(error_msg))
                    with open("update_last_season_errors.log", "a", encoding="utf-8") as log:
                        log.write(f"{timezone.now()}: {error_msg}\n")

        # Print summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("UPDATE COMPLETED!")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Successfully updated: {success_count} kits")
        self.stdout.write(f"Pages moved (removed): {not_found_count} kits")
        self.stdout.write(f"Network errors: {network_error_count} kits")
        self.stdout.write(f"Other errors: {error_count} kits")
        self.stdout.write(f"Total processed: {processed_count} kits")

        if error_count > 0 or not_found_count > 0 or network_error_count > 0:
            self.stdout.write(self.style.WARNING("Check update_last_season_errors.log for details on failures"))

        if network_error_count > 0:
            self.stdout.write(self.style.WARNING("Network errors detected - consider running again later"))

        # Reset title
        os.system("title FKApi - Update Last Season - COMPLETED")

    def _handle_moved_kit(self, kit: Kit) -> None:
        """
        Handles a kit that was moved (404 error) by checking for duplicates and removing it.

        Args:
            kit (Kit): The kit that was not found (page moved)
        """
        try:
            # Look for potential duplicates based on team, season, and type
            potential_duplicates = Kit.objects.filter(team=kit.team, season=kit.season, type=kit.type).exclude(
                id=kit.id
            )

            if potential_duplicates.exists():
                self.stdout.write(
                    self.style.WARNING(f"Found {potential_duplicates.count()} potential duplicates for {kit.slug}")
                )

                # Log the moved kit and its potential duplicates
                with open("moved_kits.log", "a", encoding="utf-8") as log:
                    log.write(f"{timezone.now()}: MOVED KIT: {kit.slug}\n")
                    for duplicate in potential_duplicates:
                        log.write(f"  Potential duplicate: {duplicate.slug}\n")

                # Remove the moved kit since we likely have the updated version
                kit_name = kit.name
                kit.delete()
                self.stdout.write(self.style.SUCCESS(f"Removed moved kit: {kit_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"No duplicates found for moved kit: {kit.slug}"))
                # Log moved kit without duplicates for manual review
                with open("moved_kits_no_duplicates.log", "a", encoding="utf-8") as log:
                    log.write(f"{timezone.now()}: MOVED KIT (no duplicates): {kit.slug}\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error handling moved kit {kit.slug}: {str(e)}"))
