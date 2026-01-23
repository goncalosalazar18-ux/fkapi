"""
Django models for the Football Kit Archive API.

This module defines all database models used in the application, including
Club, Kit, Season, Brand, Competition, Color, and related models.
"""

from colorfield.fields import ColorField
from django.core.validators import RegexValidator
from django.db import models
from django_countries.fields import CountryField


class Color(models.Model):
    """
    Represents a color used in kit designs.

    Attributes:
        name: Name of the color (e.g., "Red", "Blue")
        color: Hex color code (e.g., "#FF0000")
    """

    name = models.CharField(max_length=100)
    color = ColorField(default="#FF0000")

    def __str__(self):
        return self.name


class Variation(models.Model):
    """
    Represents a color variation (shade) of a parent color.

    Attributes:
        name: Name of the variation
        parent_color: Parent color this variation belongs to
        color: Hex color code
        color_r: Red component (0-255)
        color_g: Green component (0-255)
        color_b: Blue component (0-255)
    """

    name = models.CharField(max_length=100)
    parent_color = models.ForeignKey(Color, on_delete=models.CASCADE)
    color = ColorField(default="#FF0000")
    color_r = models.IntegerField(default=0)
    color_g = models.IntegerField(default=0)
    color_b = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Season(models.Model):
    """
    Represents a football season.

    Seasons can be in single year format (e.g., "2024") or two-year format (e.g., "2023-24").

    Attributes:
        year: Full season identifier (unique)
        first_year: First year of the season
        second_year: Second year of the season (optional, for two-year formats)
    """

    year = models.CharField(max_length=9, unique=True)
    first_year = models.CharField(max_length=4)
    second_year = models.CharField(max_length=4, blank=True, null=True)

    def __str__(self):
        return self.year


class Type_K(models.Model):  # noqa: N801
    """
    Represents the type of kit (e.g., "Home", "Away", "Third").

    Note: Model name uses Type_K to match legacy naming convention.

    Categories:
    - 'match': Game kits (default)
    - 'prematch': Pre-match, bench, warm-up, staff
    - 'preseason': Pre-season, Temporary
    - 'training': Training
    - 'travel': Travel, Polo
    - 'jacket': Jackets (Anthem, Rain, Jacket, Windbreaker, Track, vest)

    Order priority: Lower numbers appear first within category.
    Category order: 1=match, 2=prematch, 3=preseason, 4=training, 5=travel, 6=jacket
    """

    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=[
            ("match", "Game kits"),
            ("prematch", "Pre-match/Bench/Warm-up/Staff"),
            ("preseason", "Pre-season/Temporary"),
            ("training", "Training"),
            ("travel", "Travel/Polo"),
            ("jacket", "Jackets"),
        ],
        default="match",
        db_index=True,
        help_text="Category for sorting and organization",
    )
    category_order = models.IntegerField(
        default=1,
        db_index=True,
        help_text="Order of category: 1=match, 2=prematch, 3=preseason, 4=training, 5=travel, 6=jacket",
    )
    order_priority = models.IntegerField(
        default=999,
        db_index=True,
        help_text="Priority within category (lower = first). Non-GK items come before GK items.",
    )
    is_goalkeeper = models.BooleanField(
        default=False, db_index=True, help_text="True if this is a goalkeeper kit (GK, Goalkeeper, Portero)"
    )

    class Meta:
        ordering = ["category_order", "is_goalkeeper", "order_priority", "name"]
        indexes = [
            models.Index(fields=["category_order", "is_goalkeeper", "order_priority"]),
            models.Index(fields=["category", "is_goalkeeper", "order_priority"]),
        ]

    def __str__(self):
        return self.name

    def categorize(self):
        """Automatically categorize and set ordering fields based on name."""
        from core.management.commands.categorize_type_k import Command

        cmd = Command()
        category, category_order = cmd._categorize(self.name)
        is_goalkeeper = cmd._is_goalkeeper(self.name)
        order_priority = cmd._get_order_priority(self.name, category)

        self.category = category
        self.category_order = category_order
        self.is_goalkeeper = is_goalkeeper
        self.order_priority = order_priority
        return self


class Competition(models.Model):
    """
    Represents a football competition (e.g., "Premier League", "Champions League").

    Attributes:
        name: Competition name (indexed for search performance)
        slug: URL-friendly identifier (unique)
        logo: URL to competition logo
        logo_dark: URL to dark mode logo
        country: Country where competition is based (optional)
    """

    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True, max_length=150)
    logo = models.URLField(null=True, blank=True)
    logo_dark = models.URLField(null=True, blank=True)
    country = CountryField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return self.name


class Club(models.Model):
    """
    Represents a football club/team.

    Attributes:
        id_fka: Original ID from footballkitarchive.com (optional)
        name: Club name (indexed for search performance)
        slug: URL-friendly identifier (unique, allows special characters)
        logo: URL to club logo
        logo_dark: URL to dark mode logo
        country: Country where club is based (optional)
    """

    id_fka = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=500, db_index=True)
    # Custom slug field that allows special characters (The Django default slug field does not allow special characters)
    slug = models.CharField(
        unique=True,
        db_index=True,
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[-a-zA-Z0-9_ăâîșțĂÂÎȘȚ]+$",
                message="Enter a valid 'slug' consisting of letters, numbers, underscores, hyphens, or Romanian characters.",
                code="invalid_slug",
            )
        ],
    )
    logo = models.URLField(null=True, blank=True)
    logo_dark = models.URLField(null=True, blank=True)
    country = CountryField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return self.name


class Brand(models.Model):
    """
    Represents a kit manufacturer/brand (e.g., "Nike", "Adidas", "Puma").

    Attributes:
        name: Brand name (indexed for search performance)
        slug: URL-friendly identifier (unique)
        logo: URL to brand logo
        logo_dark: URL to dark mode logo
    """

    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True, max_length=150)
    logo = models.URLField(null=True, blank=True)
    logo_dark = models.URLField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class Kit(models.Model):
    """
    Represents a football kit (jersey/uniform).

    A kit belongs to a club, season, brand, and type (Home/Away/Third).
    It can have multiple competitions and colors associated with it.

    Attributes:
        name: Kit name (indexed for search performance)
        slug: URL-friendly identifier (unique, allows special characters)
        kit_id: Original ID from FootballKitArchive.com (optional)
        team: Club that owns this kit (required)
        season: Season this kit was used (required)
        competition: Competitions this kit was used in (many-to-many)
        type: Type of kit - Home, Away, Third, etc. (required)
        brand: Manufacturer/brand of the kit (required)
        main_img_url: URL to main kit image (required)
        rating: User rating (0.00-10.00)
        fh_link: Link to FootyHeadlines.com (optional)
        web_updated: Last update time from source website (optional)
        last_updated: Last update time in database (auto-updated)
        primary_color: Primary color of the kit (optional)
        secondary_color: Secondary colors of the kit (many-to-many, optional)
        design: Design description or pattern name (optional)
    """

    name = models.CharField(max_length=100, db_index=True)
    # Custom slug field that allows special characters(The Django default slug field does not allow special characters)
    slug = models.CharField(
        unique=True,
        db_index=True,
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[-a-zA-Z0-9_ăâîșțĂÂÎȘȚ]+$",
                message="Enter a valid 'slug' consisting of letters, numbers, underscores, hyphens, or Romanian characters.",
                code="invalid_slug",
            )
        ],
    )
    kit_id = models.CharField(
        max_length=20, null=True, blank=True, help_text="ID from FootballKitArchive for URL construction"
    )
    team = models.ForeignKey(Club, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    competition = models.ManyToManyField(Competition)
    type = models.ForeignKey(Type_K, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    main_img_url = models.URLField()
    rating = models.DecimalField(max_digits=3, decimal_places=2)
    fh_link = models.URLField(null=True, blank=True)
    web_updated = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    primary_color = models.ForeignKey(
        Color, on_delete=models.SET_NULL, related_name="primary_color", null=True, blank=True
    )
    secondary_color = models.ManyToManyField(Color, related_name="secondary_color", blank=True)
    design = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["team", "season"]),
            models.Index(fields=["main_img_url"]),
            models.Index(fields=["web_updated"]),
            models.Index(fields=["last_updated"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return self.name
