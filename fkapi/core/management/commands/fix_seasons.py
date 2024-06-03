# This script fixes wrong season years. If the first year is between 1875 and 1935, the second year is 19XX, not 20XX.
from core.models import Season, Kit
from django.core.management.base import BaseCommand
from django.db.models import Count, F, Value
from django.db.models.functions import Concat

class Command(BaseCommand):
    help = 'Fixes seasons and rearranges related kits'

    def handle(self, *args, **options):
        # Fix wrong season years
        # seasons_to_fix = Season.objects.filter(first_year__gte=1850, first_year__lte=1899, second_year__isnull=False)
        
        # for season in seasons_to_fix:
        #     second_splitted_year = season.year.split('-')[1]
        #     if int(season.second_year)<int(season.first_year):
        #         season.second_year = Concat(Value('18'), Value(second_splitted_year))
        #     season.save()

        #Find duplicate seasons
        duplicate_seasons = Season.objects.values('year').annotate(
            count=Count('year')
        ).filter(count__gt=1)

        # Rearrange related kits
        for season in duplicate_seasons:
            # Leave the first one
            first_season = Season.objects.filter(year=season['year']).order_by('id').first()
            # Iterate over the second unit of the duplicates
            for duplicate in Season.objects.filter(year=season['year']).order_by('id')[1:]:
                # Set the related item to the first unit
                for kit in Kit.objects.filter(season=duplicate):
                    kit.season = first_season
                    kit.save()
                # Delete the repeated units
                duplicate.delete()
                print(f'Deleted duplicated season {duplicate.year}')

        seasons=Season.objects.filter(second_year__isnull=False).order_by('year')
        for season in seasons:
            if int(season.first_year)>int(season.second_year):
                season.second_year=str(int(season.second_year)+100)
                season.save()
            elif int(season.second_year)-int(season.first_year)>35:
                season.second_year=str(int(season.second_year)-100)
                season.save()
