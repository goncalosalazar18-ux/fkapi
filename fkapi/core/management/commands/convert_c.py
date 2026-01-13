from django.core.management.base import BaseCommand

from core.models import Variation


class Command(BaseCommand):
    help = 'Converts existing Variation objects to use RGB color fields'

    def handle(self, *args, **kwargs):
        variations = Variation.objects.all()
        for variation in variations:
            # Convert the hexadecimal color to RGB
            hex_color = variation.color.lstrip('#')
            rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            # Update the Variation object with the RGB values
            variation.color_r = rgb_color[0]
            variation.color_g = rgb_color[1]
            variation.color_b = rgb_color[2]
            variation.save()

        self.stdout.write(self.style.SUCCESS('Successfully converted Variation objects to RGB'))
