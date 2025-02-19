from django.core.management.base import BaseCommand
from core.models import Kit
from django.db.models import Count
from django.utils import timezone

class Command(BaseCommand):
    help = 'Identifica y resuelve kits duplicados basados en el slug'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Resolver automáticamente manteniendo el kit más reciente',
        )

    def handle(self, *args, **options):
        # Identificar slugs duplicados
        duplicate_slugs = Kit.objects.values('slug').annotate(
            count=Count('id')).filter(count__gt=1).values_list('slug', flat=True)

        self.stdout.write(f"Se encontraron {len(duplicate_slugs)} slugs duplicados.")

        for slug in duplicate_slugs:
            kits = Kit.objects.filter(slug=slug).order_by('-last_updated')
            self.stdout.write(f"\nRevisando kits con slug: {slug}")

            for i, kit in enumerate(kits):
                self.stdout.write(f"Kit {i+1}:")
                self.stdout.write(f"  ID: {kit.id}")
                self.stdout.write(f"  Nombre: {kit.name}")
                self.stdout.write(f"  Equipo: {kit.team}")
                self.stdout.write(f"  Temporada: {kit.season}")
                self.stdout.write(f"  Última actualización: {kit.last_updated}")

            if options['auto']:
                action = 'm'
            else:
                action = input("¿Qué acción desea tomar? (m)antener el más reciente, (e)liminar duplicados, (s)altar: ")

            if action.lower() == 'm':
                # Mantener el kit más reciente y eliminar los demás
                latest_kit = kits[0]
                for kit in kits[1:]:
                    self.stdout.write(f"Eliminando kit duplicado con ID {kit.id}")
                    kit.delete()
                self.stdout.write(f"Se mantuvo el kit {latest_kit.id} y se eliminaron los demás.")
            elif action.lower() == 'e':
                # Eliminar todos los duplicados excepto el primero
                for kit in kits[1:]:
                    self.stdout.write(f"Eliminando kit duplicado con ID {kit.id}")
                    kit.delete()
                self.stdout.write(f"Se eliminaron todos los duplicados excepto el kit {kits[0].id}.")
            elif action.lower() == 's':
                self.stdout.write("Se saltó este conjunto de duplicados.")
            else:
                self.stdout.write("Acción no reconocida. Se saltó este conjunto de duplicados.")

        self.stdout.write(self.style.SUCCESS('Proceso completado.'))

        # Verificar los casos específicos mencionados
        specific_slugs = [
            'estudiantes-2024-home-kit',
            'santos-2024-home-kit',
            'bahia-2024-special-kit',
            'cusco-fc-2024-away-kit'
        ]
        for slug in specific_slugs:
            count = Kit.objects.filter(slug=slug).count()
            self.stdout.write(f"Slug '{slug}': {count} kit(s) encontrado(s)")