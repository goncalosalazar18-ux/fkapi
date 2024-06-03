from core.models import Brand
from core.scrapers import scrape_brand
from django.core.management.base import BaseCommand
import time
from django.utils.text import slugify
from concurrent.futures import ThreadPoolExecutor, as_completed

from concurrent.futures import ThreadPoolExecutor, as_completed

class Command(BaseCommand):
    help = 'Scrapes brand data from the web'

    def handle(self, *args, **options):
        brands = Brand.objects.filter(logo__isnull=True).order_by('-name')

        def scrape_brand_wrapper(brand_slugged):
            try:
                return scrape_brand(brand_slugged)
            except Exception as e:
                print(f'Error scraping {brand_slugged}: {str(e)}')
                return None

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            for brand in brands:
                print(brand)
                brand_slugged = slugify(brand.name.replace(".", "").strip()+'-kits')
                print(f'Scraping {brand.slug}')
                futures.append(executor.submit(scrape_brand_wrapper, brand_slugged))
            
            for future in as_completed(futures):
                result = future.result()
                if result is None:
                    continue  # Continue with the next brand in case of error
