from ninja import Schema
from typing import List, Optional

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
    id: Optional[int] = None
    id_fka: Optional[int] = None
    name: str
    slug: str
    logo: Optional[str] = None
    logo_dark: Optional[str] = None
    country: Optional[str] = None

class SeasonJsonSchema(Schema):
    id: Optional[int] = None
    year: str
    first_year: str
    second_year: Optional[str] = None

class CompetitionJsonSchema(Schema):
    id: Optional[int] = None
    name: str
    slug: str
    logo: Optional[str] = None
    logo_dark: Optional[str] = None
    country: Optional[str] = None


class TypeJsonSchema(Schema):
    name: str

class BrandJsonSchema(Schema):
    id: Optional[int] = None
    name: str
    slug: str
    logo: Optional[str] = None
    logo_dark: Optional[str] = None

class ColorJsonSchema(Schema):
    name: str
    color: str

class KitJsonSchema(Schema):
    name: str
    slug: str
    team: ClubJsonSchema
    season: SeasonJsonSchema
    competition: List[CompetitionJsonSchema]
    type: TypeJsonSchema
    brand: BrandJsonSchema
    design: Optional[str] = None
    primary_color: Optional[ColorJsonSchema] = None
    secondary_color: Optional[List[ColorJsonSchema]] = None
    main_img_url: str