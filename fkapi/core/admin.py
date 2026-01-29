from django.contrib import admin
from django.utils.html import format_html

from .models import Brand, Club, Color, Competition, Kit, Season, Type_K, Variation


class ColorAdmin(admin.ModelAdmin):
    list_display = ("name", "color_rectangle")

    def color_rectangle(self, obj):
        return format_html('<div style="width: 30px; height: 30px; background: {};"></div>', obj.color)

    color_rectangle.short_description = "Color"
    color_rectangle.allow_tags = True


class VariationAdmin(admin.ModelAdmin):
    list_display = ("name", "parent_color", "color_rectangle")

    def color_rectangle(self, obj):
        return format_html('<div style="width: 30px; height: 30px; background: {};"></div>', obj.color)

    color_rectangle.short_description = "Color"
    color_rectangle.allow_tags = True


class ClubAdmin(admin.ModelAdmin):
    list_display = ("logo_height", "name", "slug")
    # search by name
    search_fields = ("name", "slug")

    # set logo height
    def logo_height(self, obj):
        return format_html('<img src="{}" height="50px" />', obj.logo)

    logo_height.short_description = "Logo"
    logo_height.allow_tags = True


admin.site.register(Color, ColorAdmin)
admin.site.register(Variation, VariationAdmin)
admin.site.register(Club, ClubAdmin)


class SeasonAdmin(admin.ModelAdmin):
    list_display = ("year", "first_year", "second_year")
    ordering = ("year",)


admin.site.register(Season, SeasonAdmin)


class Type_KAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "category_order", "order_priority", "is_goalkeeper")
    list_filter = ("category", "is_goalkeeper", "category_order")
    search_fields = ("name",)
    ordering = ("category_order", "is_goalkeeper", "order_priority", "name")
    readonly_fields = ("category", "category_order", "order_priority", "is_goalkeeper")


admin.site.register(Type_K, Type_KAdmin)


class CompetitionAdmin(admin.ModelAdmin):
    search_fields = ("name", "slug")


admin.site.register(Competition, CompetitionAdmin)


class BrandAdmin(admin.ModelAdmin):
    search_fields = ("name", "logo_dark",)
    list_display = ("logo_height", "name", "slug")

    def logo_height(self, obj):
        return format_html('<img src="{}" height="50px" />', obj.logo)

    logo_height.short_description = "Logo"
    logo_height.allow_tags = True


admin.site.register(Brand, BrandAdmin)


class KitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "image_thumb",
        "slug",
        "name",
        "brand",
        "season",
        "type",
        "team",
        "design",
        "colors",
        "competitions",
    )
    readonly_fields = ("image_thumb",)
    search_fields = ("name", "slug", "id")
    list_filter = ("design", "type")

    def image_thumb(self, obj):
        return format_html('<img src="{}" height="200px" />', obj.main_img_url)

    image_thumb.short_description = "Image"
    image_thumb.allow_tags = True

    def competitions(self, obj):
        return ", ".join([competition.name for competition in obj.competition.all()])

    competitions.short_description = "Competitions"

    def colors(self, obj):
        colors_display = []
        if obj.primary_color:
            colors_display.append(
                f'<span style="display:inline-block; width:15px; height:15px; background-color:{obj.primary_color.color}; border:1px solid #ccc;"></span> {obj.primary_color.name}'
            )

        secondary_colors = [
            f'<span style="display:inline-block; width:15px; height:15px; background-color:{c.color}; border:1px solid #ccc;"></span> {c.name}'
            for c in obj.secondary_color.all()
        ]

        if colors_display or secondary_colors:
            return format_html(", ".join(colors_display + secondary_colors))
        return "-"

    colors.short_description = "Colors"
    colors.allow_tags = True


admin.site.register(Kit, KitAdmin)
