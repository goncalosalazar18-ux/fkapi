
from colorfield.fields import ColorField
from django.core.validators import RegexValidator
from django.db import models
from django_countries.fields import CountryField


class Color(models.Model):
    name = models.CharField(max_length=100)
    color = ColorField(default='#FF0000')

    def __str__(self):
        return self.name

class Variation(models.Model):
    name = models.CharField(max_length=100)
    parent_color = models.ForeignKey(Color, on_delete=models.CASCADE)
    color = ColorField(default='#FF0000')
    color_r= models.IntegerField(default=0)
    color_g= models.IntegerField(default=0)
    color_b= models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Season(models.Model):
    year = models.CharField(max_length=9,unique=True)
    first_year = models.CharField(max_length=4)
    second_year = models.CharField(max_length=4,blank=True,null=True)

    def __str__(self):
        return self.year

class Type_K(models.Model):  # noqa: N801
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Competition(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True,max_length=150)
    logo = models.URLField(null=True,blank=True)
    logo_dark = models.URLField(null=True,blank=True)
    country = CountryField(blank=True, null=True)

    def __str__(self):
        return self.name

class Club(models.Model):
    id_fka = models.IntegerField(null=True,blank=True)
    name = models.CharField(max_length=500)
    # Custom slug field that allows special characters(The Django default slug field does not allow special characters)
    slug = models.CharField(unique=True, db_index=True, max_length=150, validators=[
        RegexValidator(
            regex=r'^[-a-zA-Z0-9_ăâîșțĂÂÎȘȚ]+$',
            message="Enter a valid 'slug' consisting of letters, numbers, underscores, hyphens, or Romanian characters.",
            code='invalid_slug'
        )
    ])
    logo = models.URLField(null=True,blank=True)
    logo_dark = models.URLField(null=True,blank=True)
    country = CountryField(blank=True, null=True)

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True,max_length=150)
    logo = models.URLField(null=True,blank=True)
    logo_dark = models.URLField(null=True,blank=True)

    def __str__(self):
        return self.name

class Kit(models.Model):
    name = models.CharField(max_length=100)
    # Custom slug field that allows special characters(The Django default slug field does not allow special characters)
    slug = models.CharField(unique=True, db_index=True, max_length=150, validators=[
        RegexValidator(
            regex=r'^[-a-zA-Z0-9_ăâîșțĂÂÎȘȚ]+$',
            message="Enter a valid 'slug' consisting of letters, numbers, underscores, hyphens, or Romanian characters.",
            code='invalid_slug'
        )
    ])
    kit_id = models.CharField(max_length=20, null=True, blank=True, help_text="ID from FootballKitArchive for URL construction")
    team = models.ForeignKey(Club, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    competition = models.ManyToManyField(Competition)
    type = models.ForeignKey(Type_K, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    main_img_url = models.URLField()
    rating = models.DecimalField(max_digits=3, decimal_places=2)
    fh_link = models.URLField(null=True,blank=True)
    web_updated = models.DateTimeField(null=True,blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    primary_color = models.ForeignKey(Color, on_delete=models.SET_NULL,related_name='primary_color', null=True,blank=True)
    secondary_color = models.ManyToManyField(Color, related_name='secondary_color', blank=True)
    design = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name
