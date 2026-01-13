from django.core.management.base import BaseCommand

from core.models import Kit
from core.scrapers import scrape_kit


class Command(BaseCommand):
    help = 'Scrapea un kit específico por su slug'

    def add_arguments(self, parser):
        parser.add_argument('slug', type=str, help='Slug del kit a scrapear')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar rescrapeo incluso si el kit ya existe y usar proxy'
        )

    def handle(self, *args, **options):
        slug = options['slug']
        use_proxy = options['force']

        self.stdout.write(f"Iniciando scrapeo para slug: {slug}")

        # Verificar si el kit ya existe
        if Kit.objects.filter(slug=slug).exists() and not use_proxy:
            self.stdout.write(self.style.WARNING(f"El kit con slug {slug} ya existe. Usa --force para actualizarlo."))
            return

        try:
            result = scrape_kit(slug, use_proxy=use_proxy)
            if isinstance(result, Kit):
                self.stdout.write(self.style.SUCCESS(f"Kit {slug} scrapeado exitosamente!"))
            else:
                self.stdout.write(self.style.ERROR(f"Error al scrapear {slug}: No se pudo obtener el kit"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fatal al scrapear {slug}: {str(e)}"))
