from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from core.models import Kit
from core.scrapers import scrape_kit


class Command(BaseCommand):
    help = "Re-scrape kits"

    def handle(self, *args, **options):
        #kits = Kit.objects.all()
        with open('kits_to_fix.txt', encoding='utf-8') as file:
            kits = file.readlines()
        with ThreadPoolExecutor(max_workers=15) as executor:
            for kit in kits:
                if kit == "==========================================================\n":
                    continue
                #if slug exists, dont scrape
                if Kit.objects.filter(slug=kit.replace("\n", "")).exists():
                    continue
                executor.submit(scrape_kit, kit.replace("\n", ""), True)

