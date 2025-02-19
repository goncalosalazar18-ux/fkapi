from django.contrib import admin
from .models import Season, Type_K, Competition, Club, \
    Brand, Kit, Color, Variation
from django.utils.html import format_html


class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_rectangle')

    def color_rectangle(self, obj):
        return format_html('<div style="width: 30px; height: 30px; background: {};"></div>', obj.color)
    color_rectangle.short_description = 'Color'
    color_rectangle.allow_tags = True


class VariationAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_color', 'color_rectangle')

    def color_rectangle(self, obj):
        return format_html('<div style="width: 30px; height: 30px; background: {};"></div>', obj.color)
    color_rectangle.short_description = 'Color'
    color_rectangle.allow_tags = True


class ClubAdmin(admin.ModelAdmin):
    list_display = ('logo_height', 'name', 'slug')
    # search by name
    search_fields = ('name', 'slug')
    # set logo height
    def logo_height(self, obj):
        return format_html('<img src="{}" height="50px" />', obj.logo)
    logo_height.short_description = 'Logo'
    logo_height.allow_tags = True


admin.site.register(Color, ColorAdmin)
admin.site.register(Variation, VariationAdmin)
admin.site.register(Club, ClubAdmin)

class SeasonAdmin(admin.ModelAdmin):
    list_display = ('year', 'first_year', 'second_year')
    ordering = ('year',)

admin.site.register(Season, SeasonAdmin)
admin.site.register(Type_K)


class CompetitionAdmin(admin.ModelAdmin):
    search_fields = ('name', 'slug')


admin.site.register(Competition, CompetitionAdmin)


class BrandAdmin(admin.ModelAdmin):
    #search_fields = ('name', 'slug')
    search_fields = ('logo_dark',)
    list_display = ('logo_height', 'name', 'slug')
    def logo_height(self, obj):
        return format_html('<img src="{}" height="50px" />', obj.logo)
    logo_height.short_description = 'Logo'
    logo_height.allow_tags = True


admin.site.register(Brand, BrandAdmin)


class KitAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_thumb', 'name', 'brand',
                    'season', 'type', 'team', 'competitions')
    readonly_fields = ('image_thumb',)
    search_fields = ('name', 'slug','id')

    def image_thumb(self, obj):
        return format_html('<img src="{}" height="200px" />', obj.main_img_url)
    image_thumb.short_description = 'Image'
    image_thumb.allow_tags = True

    def competitions(self, obj):
        return ", ".join([competition.name for competition in obj.competition.all()])
    competitions.short_description = 'Competitions'


admin.site.register(Kit, KitAdmin)
