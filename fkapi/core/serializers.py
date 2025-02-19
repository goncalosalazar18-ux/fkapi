from ninja import Schema
from typing import List

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
    name: str
    slug: str
    logo: str

class SeasonJsonSchema(Schema):
    year: str
    first_year: str
    second_year: str | None

class CompetitionJsonSchema(Schema):
    name: str
    slug: str
    logo: str

class TypeJsonSchema(Schema):
    name: str

class BrandJsonSchema(Schema):
    name: str
    slug: str
    logo: str

class KitJsonSchema(Schema):
    name: str
    slug: str
    team: ClubJsonSchema
    season: SeasonJsonSchema
    competition: List[CompetitionJsonSchema]
    type: TypeJsonSchema
    brand: BrandJsonSchema
    main_img_url: str