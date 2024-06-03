# from django.core.management.base import BaseCommand
# from core.models import Kit, Variation
# from colorgram import extract, Color
# from rembg import remove
# import requests
# # import colorgram


# def rgb_distance(rgb1, rgb2):
#     r1, g1, b1 = rgb1
#     r2, g2, b2 = rgb2
#     return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5


# class Command(BaseCommand):
#     help = 'Extracts the dominant colors from the images of the kits'

#     def handle(self, *args, **kwargs):
#         print("Extracting colors...")
#         kits = Kit.objects.filter(
#             main_img_url__isnull=False, primary_color=None, secondary_color=None)
#         for kit in kits:
#             # Get the image and remove bg
#             print(f"Extracting colors for {kit.name}...")
#             # Download the image

#             # with open("output.png", "wb") as f:
#             #     f.write(remove(requests.get(kit.main_img_url).content))
#             # print("Got the image without background...")

#             # Extract colors from the modified image
#             # Extract the 2 most dominant colors from the image
#             colors = extract("output.png", 2)
#             print(colors)
#             print("Extracted colors...")
#             print("Trying to match colors...")
#             # Encontrar las variaciones que mejor se aproximan a los colores extraídos
#             for i, color in enumerate(colors):
#                 # Aqui iria el codigo para encontrar la variacion mas cercana
#                 closest_variation = min(Variation.objects.all(),
#                                         key=lambda v: rgb_distance(color.rgb, (v.color_r, v.color_g, v.color_b)))
#                 if i == 0:
#                     kit.primary_color = closest_variation
#                     print(
#                         f"Primary color for {kit.name} is {closest_variation}")
#                 else:
#                     kit.secondary_color = closest_variation
#                     print(
#                         f"Secondary color for {kit.name} is {closest_variation}")
#             kit.save()
#             print(f"Colors for {kit.name} extracted successfully...")
