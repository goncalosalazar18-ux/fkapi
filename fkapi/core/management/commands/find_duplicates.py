from django.core.management.base import BaseCommand
from django.db.models import Count
from core.models import Brand, Competition, Club, Kit, Season

class Command(BaseCommand):
    help = 'Finds duplicate slugs for brands, competitions, clubs and kits'

    def handle(self, *args, **options):
        # Find duplicate slugs for brands
        duplicate_brands = Brand.objects.values('slug').annotate(Count('id')).order_by().filter(id__count__gt=1)
        print("Duplicate Brand Slugs:")
        for brand in duplicate_brands:
            print(brand['slug'])
        
        # Find duplicate slugs for competitions  
        duplicate_competitions = Competition.objects.values('slug').annotate(Count('id')).order_by().filter(id__count__gt=1)
        print("Duplicate Competition Slugs:")
        for competition in duplicate_competitions:
            print(competition['slug'])
        
        # Find duplicate slugs for clubs
        duplicate_clubs = Club.objects.values('slug').annotate(Count('id')).order_by().filter(id__count__gt=1)  
        print("Duplicate Club Slugs:")
        for club in duplicate_clubs:
            print(club['slug'])
        
        # Find duplicate slugs for kits
        duplicate_kits = Kit.objects.values('slug').annotate(Count('id')).order_by().filter(id__count__gt=1)
        print("Duplicate Kit Slugs:")  
        for kit in duplicate_kits:
            print(kit['slug'])

        # Find year for seasons
        duplicate_seasons = Season.objects.values('year').annotate(Count('id')).order_by().filter(id__count__gt=1)
        print("Duplicate Season Slugs:")
        for season in duplicate_seasons:
            print(season['slug'])

