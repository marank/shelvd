from uuid import UUID

from ninja import Schema

from ..models import Company, MediaType, Platform
from ..selectors.terms import description_for


class PlatformOut(Schema):
    id: UUID
    name: str
    short_name: str
    slug: str
    manufacturer: str
    media_type: str
    release_year: int | None
    color: str  # "#e60012", empty = the manufacturer's
    icon: str  # PlatformIcon key or empty
    icon_url: str | None  # an uploaded icon, which wins over `icon`
    icon_dark: bool  # the icon is a dark mark: invert it on dark backgrounds

    @staticmethod
    def resolve_icon_url(obj: Platform) -> str | None:
        return obj.icon_image.url if obj.icon_image else None


class PlatformListOut(PlatformOut):
    """For the platforms page: pictures, facts and how many games the catalog has."""

    image_url: str | None
    photo_url: str | None
    image_tone: str  # how logo and photo read: black/dark/white/light or "" (services.tones)
    photo_tone: str
    generation: int | None
    discontinued: int | None
    game_count: int

    @staticmethod
    def resolve_image_url(obj: Platform) -> str | None:
        return obj.image.url if obj.image else None

    @staticmethod
    def resolve_photo_url(obj: Platform) -> str | None:
        return obj.photo.url if obj.photo else None


class PlatformRefOut(Schema):
    """Another platform (a predecessor, a successor), enough for its badge."""

    id: UUID
    name: str
    short_name: str
    manufacturer: str
    color: str
    icon: str
    icon_url: str | None
    icon_dark: bool

    @staticmethod
    def resolve_icon_url(obj: Platform) -> str | None:
        return obj.icon_image.url if obj.icon_image else None


class ManufacturerOut(Schema):
    """The catalog company the manufacturer's name is (for a link to its page)."""

    id: UUID
    name: str


class PlatformDetailOut(PlatformOut):
    """For the platform's page and edit page: picture, description (the reader's language,
    else another), facts, its IGDB id and whether it can be deleted."""

    igdb_id: int | None
    release_count: int
    image_url: str | None  # the logo
    photo_url: str | None  # a photo of the device
    image_tone: str  # how they read: black/dark/white/light or "" (services.tones)
    photo_tone: str
    description: str
    description_language: str
    descriptions: dict[str, str]
    generation: int | None
    discontinued: int | None
    manufacturer_company: ManufacturerOut | None
    predecessors: list[PlatformRefOut]
    successors: list[PlatformRefOut]
    can_describe: bool  # linked to a source (pictures can be chosen)

    @staticmethod
    def resolve_image_url(obj: Platform) -> str | None:
        return obj.image.url if obj.image else None

    @staticmethod
    def resolve_photo_url(obj: Platform) -> str | None:
        return obj.photo.url if obj.photo else None

    @staticmethod
    def resolve_description(obj: Platform) -> str:
        return description_for(obj.descriptions)[0]

    @staticmethod
    def resolve_description_language(obj: Platform) -> str:
        return description_for(obj.descriptions)[1]

    @staticmethod
    def resolve_manufacturer_company(obj: Platform) -> Company | None:
        if not obj.manufacturer:
            return None
        return Company.objects.filter(name__iexact=obj.manufacturer).order_by("name").first()

    @staticmethod
    def resolve_predecessors(obj: Platform) -> list[Platform]:
        return list(obj.predecessors.order_by("release_year", "name"))

    @staticmethod
    def resolve_successors(obj: Platform) -> list[Platform]:
        return list(obj.successors.order_by("release_year", "name"))

    @staticmethod
    def resolve_can_describe(obj: Platform) -> bool:
        return bool(obj.external_ids)

    @staticmethod
    def resolve_igdb_id(obj: Platform) -> int | None:
        value = obj.external_ids.get("igdb")
        return int(value) if value is not None else None

    @staticmethod
    def resolve_release_count(obj: Platform) -> int:
        return obj.releases.count()


class PlatformIn(Schema):
    name: str
    short_name: str = ""
    manufacturer: str = ""
    media_type: MediaType = MediaType.GAME
    release_year: int | None = None
    color: str = ""
    icon: str = ""  # PlatformIcon key
    igdb_id: int | None = None
    descriptions: dict[str, str] = {}
    generation: int | None = None
    discontinued: int | None = None
    predecessors: list[UUID] = []


class PlatformPatch(Schema):
    name: str | None = None
    short_name: str | None = None
    manufacturer: str | None = None
    media_type: MediaType | None = None
    release_year: int | None = None
    color: str | None = None
    icon: str | None = None
    igdb_id: int | None = None
    descriptions: dict[str, str] | None = None  # by language; "" removes one
    generation: int | None = None
    discontinued: int | None = None
    predecessors: list[UUID] | None = None


class CompanyOut(Schema):
    id: UUID
    name: str


class GenreOut(Schema):
    id: UUID
    name: str
