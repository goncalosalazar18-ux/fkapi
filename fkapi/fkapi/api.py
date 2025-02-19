# Standard library imports
from contextlib import contextmanager
from typing import List

# Third-party imports
import requests
from django.db import connection, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI

# Local imports
from core.models import Club, Kit, Season
from core.serializers import (
    BrandJsonSchema,
    ClubJsonSchema,
    ClubSerializer,
    CompetitionJsonSchema,
    KitJsonSchema,
    KitSerializer,
    SeasonJsonSchema,
    SeasonSerializer,
    TypeJsonSchema,
)
from core.serializers import (
    KitJsonSchema,
    ClubJsonSchema,
    SeasonJsonSchema,
    CompetitionJsonSchema,
    TypeJsonSchema,
    BrandJsonSchema,
)


api = NinjaAPI()

# Clubs (Search by keyword)


@contextmanager
def db_connection():
    try:
        yield
    finally:
        connection.close()


@api.get("/clubs/search", response=List[ClubSerializer])
def search_clubs(request, keyword: str):
    with transaction.atomic():
        clubs = Club.objects.filter(
            Q(name__trigram_word_similar=keyword)
            | Q(slug__trigram_word_similar=keyword)
        ).order_by("id")[:10]
        return clubs


# Get kits by season and club


@api.get("/kits", response=List[KitSerializer])
def get_kits(request, club: int, season: int):
    kits = Kit.objects.filter(season__id=season, team__id=club)
    return kits


@api.get("/seasons", response=List[SeasonSerializer])
def get_seasons(request, id):
    """
    Returns available season from a club by id
    """
    club = Club.objects.get(id=id)
    kits = Kit.objects.filter(team=club).select_related("season").distinct("season")
    seasons = sorted([kit.season for kit in kits], key=lambda x: x.year, reverse=True)
    return seasons


@api.get("/kit-json/{kit_id}")
def get_kit_json(request, kit_id: int):
    kit = get_object_or_404(Kit, id=kit_id)
    return KitJsonSchema(
        name=kit.name,
        slug=kit.slug,
        team=ClubJsonSchema(name=kit.team.name, slug=kit.team.slug, logo=kit.team.logo),
        season=SeasonJsonSchema(
            year=kit.season.year,
            first_year=kit.season.first_year,
            second_year=kit.season.second_year,
        ),
        competition=[
            CompetitionJsonSchema(name=c.name, slug=c.slug, logo=c.logo)
            for c in kit.competition.all()
        ],
        type=TypeJsonSchema(name=kit.type.name),
        brand=BrandJsonSchema(
            name=kit.brand.name, slug=kit.brand.slug, logo=kit.brand.logo
        ),
        main_img_url=kit.main_img_url,
    )


@api.get("/send-kit/{kit_id}")
def send_kit(request, kit_id: int):
    try:
        kit = Kit.objects.get(id=kit_id)
        print(kit)
        competition_logo_default = (
            "https://www.footballkitarchive.com/static/logos/not_found.png"
        )
        formatted_competitions = [
            CompetitionJsonSchema(
                name=comp.name,
                slug=comp.slug,
                logo=comp.logo if comp.logo else competition_logo_default,
            )
            for comp in kit.competition.all()
        ]
        formatted_kit = KitJsonSchema(
            name=kit.name,
            slug=kit.slug,
            team=ClubJsonSchema(
                name=kit.team.name, slug=kit.team.slug, logo=kit.team.logo
            ),
            season=SeasonJsonSchema(
                year=kit.season.year,
                first_year=kit.season.first_year,
                second_year=kit.season.second_year,
            ),
            competition=formatted_competitions,
            type=TypeJsonSchema(name=kit.type.name),
            brand=BrandJsonSchema(
                name=kit.brand.name, slug=kit.brand.slug, logo=kit.brand.logo
            ),
            main_img_url=kit.main_img_url,
        )

        # Enviar los datos formateados al endpoint
        response = requests.post(
            "http://localhost:8888/api/kits/", json=formatted_kit.dict()
        )
        response.raise_for_status()

        return JsonResponse(
            {"message": "Kit enviado exitosamente", "response": response.json()}
        )
    except Kit.DoesNotExist:
        return JsonResponse({"error": "Kit no encontrado"}, status=404)
    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"Error al enviar datos a la API: {str(e)}"}, status=500
        )
