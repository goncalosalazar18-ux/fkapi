import json

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from unidecode import unidecode

from core.models import Brand, Club, Competition, Type_K


class Command(BaseCommand):
    help = 'Creates instances of the models based on data.html'

    def handle(self, *args, **kwargs):
        with open('data.html', encoding='utf-8') as file:
            data = file.read()
        soup = BeautifulSoup(data, 'html.parser')

        # Crear instancias de Type
        types = json.loads(soup.find_all('script')[0].string.split(
            'var types = ')[1].split(';')[0])
        for type_k in types:
            Type_K.objects.get_or_create(name=type_k)

        # Crear instancias de Competition
        leagues = json.loads(soup.find_all('script')[0].string.split(
            'var leagues = ')[1].split(';')[0])
        for league in leagues:
            slug = unidecode(league).replace(' ', '-').lower()+'-kits'
            Competition.objects.get_or_create(name=league, slug=slug)

        # Crear instancias de Club
        teams = json.loads(soup.find_all('script')[0].string.split(
            'var teams = ')[1].split(';')[0])
        for team in teams:
            slug = unidecode(team).replace(' ', '-').lower()+'-kits'
            Club.objects.get_or_create(name=team, slug=slug)

        # Crear instancias de Brand
        brands = json.loads(soup.find_all('script')[0].string.split(
            'var brands = ')[1].split(';')[0])
        for brand in brands:
            slug = unidecode(brand).replace(' ', '-').lower()+'-kits'
            Brand.objects.get_or_create(name=brand, slug=slug)
