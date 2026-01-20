
from ninja import Schema


class ClubSerializer(Schema):
    id: int
    name: str
    slug: str
    logo: str
    #logo_dark: str = None

    def __init__(self, instance=None):
        super().__init__(instance)


class KitSerializer(Schema):
    id: int
    name: str
    # team: str
    # season: str
    main_img_url: str


class SeasonSerializer(Schema):
    id: int
    year: str


class ClubJsonSchema(Schema):
    id: int | None = None
    id_fka: int | None = None
    name: str
    slug: str
    logo: str | None = None
    logo_dark: str | None = None
    country: str | None = None

class SeasonJsonSchema(Schema):
    id: int | None = None
    year: str
    first_year: str
    second_year: str | None = None

class CompetitionJsonSchema(Schema):
    id: int | None = None
    name: str
    slug: str
    logo: str | None = None
    logo_dark: str | None = None
    country: str | None = None


class TypeJsonSchema(Schema):
    name: str

class BrandJsonSchema(Schema):
    id: int | None = None
    name: str
    slug: str
    logo: str | None = None
    logo_dark: str | None = None

class ColorJsonSchema(Schema):
    name: str
    color: str

class KitJsonSchema(Schema):
    name: str
    slug: str
    team: ClubJsonSchema
    season: SeasonJsonSchema
    competition: list[CompetitionJsonSchema]
    type: TypeJsonSchema
    brand: BrandJsonSchema
    design: str | None = None
    primary_color: ColorJsonSchema | None = None
    secondary_color: list[ColorJsonSchema] | None = None
    main_img_url: str
