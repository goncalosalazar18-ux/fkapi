from ninja import NinjaAPI
from core.models import Club, Season, Kit
from core.serializers import ClubSerializer
from typing import List
from django.db.models import Q

api = NinjaAPI()

# Clubs (Search by keyword)


@api.get("/clubs/search", response=List[ClubSerializer])
def search_clubs(request, keyword: str):
    clubs = Club.objects.filter(
        Q(name__trigram_word_similar=keyword) | Q(
            slug__trigram_word_similar=keyword)
    )[:10].order_by('id')
    return clubs


# Get kits by season and club
from core.serializers import KitSerializer

@api.get("/kits", response=List[KitSerializer])
def get_kits(request, starting_year: int, club: int, ending_year: int = None):
    if ending_year is None:
        kits = Kit.objects.filter(season__year=starting_year, team=club)
    else:
        kits = Kit.objects.filter(
            season__year=str(starting_year) + "-" + str(ending_year)[2:], team=club)
    return kits
