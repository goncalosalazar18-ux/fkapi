# This script fixes wrong season years. If the first year is between 1875 and 1935, the second year is 19XX, not 20XX.
import csv
import logging
import os
from datetime import datetime

from django.core.management.base import BaseCommand

from core.models import Kit, Season

# Configure logging
logging.basicConfig(
    filename='problematic_seasons.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class Command(BaseCommand):
    help = 'Identifies problematic seasons and reassigns their kits to correct seasons'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes'
        )
        parser.add_argument(
            '--generate-report',
            action='store_true',
            help='Generate a detailed CSV report of all changes to be made'
        )
        parser.add_argument(
            '--apply-from-file',
            type=str,
            help='Apply changes from a specific CSV file (format: changes_to_apply.csv)'
        )

    def normalize_year(self, year_str):
        """Normalize a year string to a full year number."""
        if len(year_str) == 2:
            # For two digit years, if it's less than 50, assume 2000s, otherwise 1900s
            year_num = int(year_str)
            if year_num < 50:
                return 2000 + year_num
            return 1900 + year_num
        return int(year_str)

    def find_correct_season(self, kit_slug):
        """Extract the correct season from kit slug."""
        try:
            # Example: manchester-united-2023-24-home-kit or manchester-united-2023-home-kit
            parts = kit_slug.split('-')
            year_parts = []
            for part in parts:
                if part.isdigit() and len(part) == 4:
                    year_parts.append(part)
                elif part.isdigit() and len(part) == 2:
                    if len(year_parts) > 0:  # If we already have the first year
                        # Handle cases like '23' in '2023-24'
                        year_parts.append(part)

            if len(year_parts) == 2:
                # Case: 2023-24
                season_str = f"{year_parts[0]}-{year_parts[1]}"
            elif len(year_parts) == 1:
                # Case: 2023
                season_str = year_parts[0]
            else:
                return None

            # Try to get existing season or create new one
            season, created = Season.objects.get_or_create(
                year=season_str,
                defaults={
                    'first_year': year_parts[0],
                    'second_year': year_parts[1] if len(year_parts) > 1 else None
                }
            )
            return season
        except Exception as e:
            logging.error(f"Error processing kit slug {kit_slug}: {str(e)}")
            return None

    def update_kit_name(self, kit, new_season):
        """Update kit name to reflect the new season."""
        try:
            # Try to find the season part in the kit name and replace it
            old_season_str = str(kit.season.year)
            new_season_str = str(new_season.year)

            # If the season is in the name, replace it
            if old_season_str in kit.name:
                new_name = kit.name.replace(old_season_str, new_season_str)
                return new_name

            # If we can't find the exact season string, try a more complex approach
            # Most kit names follow the pattern: "Team Name Season Type"
            # Example: "Manchester United 2023-24 Home"
            team_name = kit.team.name
            kit_type = kit.type.name

            # Create a new name with the correct season
            new_name = f"{team_name} {new_season_str} {kit_type}"
            return new_name
        except Exception as e:
            logging.error(f"Error updating kit name for {kit.slug}: {str(e)}")
            return kit.name  # Return original name if there's an error

    def generate_csv_report(self, changes):
        """Generate a detailed CSV report of all changes to be made."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"season_changes_{timestamp}.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['action', 'kit_id', 'kit_slug', 'kit_name', 'new_kit_name', 'team_name',
                         'old_season_id', 'old_season', 'new_season_id', 'new_season', 'apply']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for change in changes:
                writer.writerow(change)

        self.stdout.write(self.style.SUCCESS(
            f"Generated report file: {filename} with {len(changes)} potential changes"
        ))
        return filename

    def apply_changes_from_file(self, filename):
        """Apply changes from a specific CSV file."""
        if not os.path.exists(filename):
            self.stdout.write(self.style.ERROR(f"File not found: {filename}"))
            return

        changes_applied = 0
        seasons_deleted = 0

        with open(filename, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                # Only apply changes marked with 'yes' in the 'apply' column
                if row['apply'].lower() != 'yes':
                    continue

                if row['action'] == 'move_kit':
                    try:
                        kit = Kit.objects.get(id=int(row['kit_id']))
                        new_season = Season.objects.get(id=int(row['new_season_id']))

                        # Update kit's season and name
                        kit.season = new_season

                        # Update kit name if provided in CSV, otherwise generate it
                        if 'new_kit_name' in row and row['new_kit_name']:
                            kit.name = row['new_kit_name']
                        else:
                            kit.name = self.update_kit_name(kit, new_season)

                        kit.save()

                        self.stdout.write(
                            f"Moved kit {kit.slug} from season {row['old_season']} to {new_season.year} "
                            f"and updated name to '{kit.name}'"
                        )
                        changes_applied += 1
                    except (Kit.DoesNotExist, Season.DoesNotExist) as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error applying change for kit {row['kit_slug']}: {str(e)}"
                        ))

                elif row['action'] == 'delete_season':
                    try:
                        season = Season.objects.get(id=int(row['old_season_id']))

                        # Check if season is empty
                        if Kit.objects.filter(season=season).count() == 0:
                            season_year = season.year
                            season.delete()
                            self.stdout.write(f"Deleted empty season: {season_year}")
                            seasons_deleted += 1
                        else:
                            self.stdout.write(self.style.WARNING(
                                f"Season {season.year} still has kits - not deleted"
                            ))
                    except Season.DoesNotExist as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error deleting season {row['old_season']}: {str(e)}"
                        ))

        self.stdout.write(self.style.SUCCESS(
            f"Applied {changes_applied} kit changes and deleted {seasons_deleted} empty seasons from {filename}"
        ))

    def handle(self, *args, **options):
        # If applying changes from file
        if options['apply_from_file']:
            self.apply_changes_from_file(options['apply_from_file'])
            return

        dry_run = options['dry_run']
        generate_report = options['generate_report']

        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")

        current_year = datetime.now().year
        problematic_seasons = []
        all_changes = []

        # Find problematic seasons
        for season in Season.objects.all():
            try:
                first_year = int(season.first_year)
                if not season.second_year:
                    # Single year season - check if it's realistic
                    if first_year > current_year + 1 or first_year < 1850:
                        problematic_seasons.append(season)
                    continue

                second_year = self.normalize_year(season.second_year)

                # Identify clearly problematic cases
                if (second_year < first_year or  # Second year before first year
                    second_year - first_year > 3 or  # Gap too large
                    first_year > current_year + 1 or  # Future years
                    second_year > current_year + 1 or  # Future years
                    first_year < 1850):  # Too old
                    problematic_seasons.append(season)

            except ValueError as e:
                logging.error(f"Error processing season {season.year}: {str(e)}")
                problematic_seasons.append(season)

        if not problematic_seasons:
            self.stdout.write(self.style.SUCCESS("No problematic seasons found."))
            return

        self.stdout.write(f"Found {len(problematic_seasons)} problematic seasons")

        # Process kits from problematic seasons
        for season in problematic_seasons:
            kits = Kit.objects.filter(season=season)
            kit_count = kits.count()

            if kit_count == 0:
                # Log season with no kits and delete it
                msg = f"Would delete season with no kits: {season.year}" if dry_run else f"Deleting season with no kits: {season.year}"
                logging.info(msg)
                self.stdout.write(msg)

                # Add to changes list
                all_changes.append({
                    'action': 'delete_season',
                    'kit_id': '',
                    'kit_slug': '',
                    'kit_name': '',
                    'new_kit_name': '',
                    'team_name': '',
                    'old_season_id': season.id,
                    'old_season': season.year,
                    'new_season_id': '',
                    'new_season': '',
                    'apply': 'yes'  # Default to yes for empty seasons
                })

                if not dry_run and not generate_report:
                    season.delete()
                continue

            self.stdout.write(f"Processing {kit_count} kits from season {season.year}")

            # Process each kit
            for kit in kits:
                correct_season = self.find_correct_season(kit.slug)

                if correct_season and correct_season != season:
                    # Generate new kit name
                    new_kit_name = self.update_kit_name(kit, correct_season)

                    # Log the change
                    msg = (f"Would move kit {kit.slug} from season {season.year} to {correct_season.year} "
                          f"and rename from '{kit.name}' to '{new_kit_name}'"
                          if dry_run or generate_report else
                          f"Moving kit {kit.slug} from season {season.year} to {correct_season.year} "
                          f"and renaming from '{kit.name}' to '{new_kit_name}'")
                    logging.info(msg)
                    self.stdout.write(msg)

                    # Add to changes list
                    all_changes.append({
                        'action': 'move_kit',
                        'kit_id': kit.id,
                        'kit_slug': kit.slug,
                        'kit_name': kit.name,
                        'new_kit_name': new_kit_name,
                        'team_name': kit.team.name,
                        'old_season_id': season.id,
                        'old_season': season.year,
                        'new_season_id': correct_season.id,
                        'new_season': correct_season.year,
                        'apply': 'no'  # Default to no for manual review
                    })

                    # Update kit's season and name
                    if not dry_run and not generate_report:
                        kit.season = correct_season
                        kit.name = new_kit_name
                        kit.save()
                else:
                    # Log kits that couldn't be reassigned
                    msg = f"Could not determine correct season for kit: {kit.slug} (current season: {season.year})"
                    logging.warning(msg)
                    self.stdout.write(self.style.WARNING(msg))

            # Check if season is now empty after potential reassignments
            if not dry_run and not generate_report:
                remaining_kits = Kit.objects.filter(season=season).count()
                if remaining_kits == 0:
                    msg = f"Deleting empty season after reassignment: {season.year}"
                    logging.info(msg)
                    self.stdout.write(msg)
                    season.delete()
                else:
                    msg = f"Season {season.year} still has {remaining_kits} kits after processing"
                    logging.warning(msg)
                    self.stdout.write(self.style.WARNING(msg))

        # Generate CSV report if requested
        if generate_report and all_changes:
            report_file = self.generate_csv_report(all_changes)
            self.stdout.write(self.style.SUCCESS(
                f"To apply these changes, review the CSV file and then run:\n"
                f"python manage.py fix_seasons --apply-from-file={report_file}"
            ))
        elif dry_run:
            status = "Would be processed" if dry_run else "Processed"
            self.stdout.write(self.style.SUCCESS(
                f"Finished! {status} {len(problematic_seasons)} problematic seasons. "
                "Check problematic_seasons.log for details."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Finished! Processed {len(problematic_seasons)} problematic seasons. "
                "Check problematic_seasons.log for details."
            ))
