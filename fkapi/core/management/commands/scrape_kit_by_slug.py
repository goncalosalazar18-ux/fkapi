from django.core.management.base import BaseCommand

from core.models import Kit
from core.scrapers import scrape_kit


class Command(BaseCommand):
    help = 'Scrape a specific kit by its slug'

    def add_arguments(self, parser):
        parser.add_argument('slug', type=str, help='Slug of the kit to scrape')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rescraping even if the kit already exists and use proxy'
        )

    def handle(self, *args, **options):
        slug = options['slug']
        use_proxy = options['force']

        self.stdout.write(f"Starting scrape for slug: {slug}")

        # Check if the kit already exists
        if Kit.objects.filter(slug=slug).exists() and not use_proxy:
            self.stdout.write(self.style.WARNING(
                f"Kit with slug {slug} already exists. Use --force to update it."
            ))
            return

        try:
            result = scrape_kit(slug, use_proxy=use_proxy)
            if isinstance(result, Kit):
                self.stdout.write(self.style.SUCCESS(f"Kit {slug} scraped successfully!"))
            else:
                self.stdout.write(self.style.ERROR(f"Error scraping {slug}: Could not obtain the kit"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Fatal error scraping {slug}: {str(e)}"))
