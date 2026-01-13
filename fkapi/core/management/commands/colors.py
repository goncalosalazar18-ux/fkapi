from django.core.management.base import BaseCommand

from core.models import Color, Variation

# Definir tus propios colores
custom_colors = {
    'Yellow': '#FFFF00',
    'Fluor Yellow': '#FFFF00',
    'Yellowgreen': '#9ACD32',
    'Pinneaple': '#FFC0CB',
    'Lemon': '#FFFACD',
    'Mustard': '#FFDB58',
    'Canary Yellow': '#FFEF00',
    'Red': '#FF0000',
    'Fluor Red': '#FF0000',
    'Maroon': '#800000',
    'Firebrick': '#B22222',
    'Green': '#008000',
    'Fluor Green': '#008000',
    'Pistachio': '#93C572',
    'Olive': '#808000',
    'Dark Olive': '#556B2F',
    'Forest': '#228B22',
    'Blue': '#0000FF',
    'Fluor Blue': '#0000FF',
    'SkyBlue': '#87CEEB',
    'Electric Blue': '#7DF9FF',
    'Turquoise': '#40E0D0',
    'Teal': '#008080',
    'Navy': '#000080',
    'Magenta': '#FF00FF',
    'Fluor Magenta': '#FF00FF',
    'Deep Pink': '#FF1493',
    'Pale pink': '#FFC0CB',
    'Bubblegum': '#FFC0CB',
    'Purple': '#800080',
    'Fluor purple': '#800080',
    'Plum': '#DDA0DD',
    'Violet': '#EE82EE',
    'Indigo': '#4B0082',
    'Deep Purple': '#9932CC',
    'Orange': '#FFA500',
    'Fluor Orange': '#FFA500',
    'Coral': '#FF7F50',
    'Tomato': '#FF6347',
    'Black': '#000000',
    'Brown': '#A52A2A',
    'Chocolate': '#D2691E',
    'Saddlebrown': '#8B4513',
    'Tan': '#D2B48C',
    'Gray': '#808080',
    'Dark Gray': '#A9A9A9',
    'Cement': '#D2B48C',
    'Ligth gray': '#D3D3D3',
    'Silver': '#C0C0C0',
    'Shiny silver': '#E6E8FA',
    'Gold': '#FFD700',
    'Goldenrod': '#DAA520',
    'Darkgoldenrod': '#B8860B',
    'White': '#FFFFFF',
    'Ivory': '#FFFFF0',
    'Cream': '#FFFDD0',
    'Wheat': '#F5DEB3',
}

class Command(BaseCommand):
    help = 'Creates instances of the models based on the color list'

    def handle(self, *args, **kwargs):
        colors = [
            'Yellow',
            'Red',
            'Green',
            'Blue',
            'Magenta',
            'Purple',
            'Orange',
            'Black',
            'Brown',
            'Gray',
            'Silver',
            'Gold',
            'White',
        ]
        for color in colors:
            hex_color = custom_colors.get(color, '#000000')  # Obtener el color del diccionario, o '#000000' si no está definido
            Color.objects.get_or_create(name=color, color=hex_color)

        variations = {
            'Yellow': [
                'Fluor Yellow',
                'Yellowgreen',
                'Pinneaple',
                'Lemon',
                'Mustard',
                'Canary Yellow',
            ],
            'Red': [
                'Fluor Red',
                'Maroon',
                'Firebrick',
            ],
            'Green': [
                'Fluor Green',
                'Pistachio',
                'Olive',
                'Dark Olive',
                'Forest',
            ],
            'Blue': [
                'Fluor Blue',
                'SkyBlue',
                'Electric Blue',
                'Turquoise',
                'Teal',
                'Navy',
            ],
            'Magenta': [
                'Fluor Magenta',
                'Deep Pink',
                'Pale pink',
                'Bubblegum',
            ],
            'Purple': [
                'Fluor purple',
                'Plum',
                'Violet',
                'Indigo',
                'Deep Purple',
            ],
            'Orange': [
                'Fluor Orange',
                'Coral',
                'Tomato',
            ],
            'Black': [
                'Black',
            ],
            'Brown': [
                'Chocolate',
                'Saddlebrown',
                'Tan',
            ],
            'Gray': [
                'Dark Gray',
                'Cement',
                'Ligth gray',
            ],
            'Silver': [
                'Shiny silver',
                'Silver',
            ],
            'Gold': [
                'Gold',
                'Goldenrod',
                'Darkgoldenrod',
            ],
            'White': [
                'White',
                'Ivory',
                'Cream',
                'Wheat',
            ],
        }
        for color, variation_list in variations.items():
            color_instance = Color.objects.get(name=color)
            for variation in variation_list:
                hex_color = custom_colors.get(variation, '#000000')  # Obtener el color del diccionario, o '#000000' si no está definido
                Variation.objects.get_or_create(name=variation, parent_color=color_instance, color=hex_color)
