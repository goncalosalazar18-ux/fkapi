from django.core.management.base import BaseCommand

from core.models import Club


class Command(BaseCommand):
    help = "Removes apostrophes from club slugs"

    def handle(self, *args, **options):
        clubs_to_fix = Club.objects.filter(slug__contains='/')
        for club in clubs_to_fix:
            club.slug = club.slug.replace('/', '-')
            club.save()
