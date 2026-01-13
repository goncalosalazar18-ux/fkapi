import time

from django.core.management.base import BaseCommand

from core.models import Brand


class Command(BaseCommand):
    help = 'Fix dark logo'

    def handle(self, *args, **options):
        # Find brands with slugs that don't end on '-kits'
        brands = Brand.objects.filter(logo__icontains='_l')
        print(f"Brands with bad slugs: {brands.count()}")
        time.sleep(10)
        for brand in brands:
            logo_dark=brand.logo
            brand.logo=logo_dark.replace('_l','')
            brand.logo_dark=logo_dark
            brand.save()



