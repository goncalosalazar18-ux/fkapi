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
    #team: str
    #season: str
    main_img_url: str
