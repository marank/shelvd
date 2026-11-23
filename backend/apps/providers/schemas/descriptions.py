from typing import Literal

from ninja import Schema


class DescriptionCandidateOut(Schema):
    """An encyclopedia entry that may describe a company or series."""

    external_id: str
    title: str
    label: str  # what it is, e.g. "Japanese video game company"
    text: str  # "" for a company entry without an article: facts only
    language: str  # the text's: the reader's, else another ("" without text)
    confident: bool  # surely this one: the right kind of thing, exactly that name
    has_image: bool  # a logo that can be taken along


class DescriptionApplyIn(Schema):
    external_id: str
    image: bool = False  # take the entry's logo as the picture (replacing it)


class DescriptionApplyOut(Schema):
    description: str
    image: bool  # whether the logo was taken


class ImageCandidateOut(Schema):
    source: str
    label: str
    kind: Literal["logo", "icon", "photo"]  # icon: a small logo
    token: str


class ImageTakeIn(Schema):
    token: str
    # photo, icon: a platform's photo of the device, its badge's icon
    target: Literal["image", "photo", "icon"] = "image"


class ImageTakenOut(Schema):
    image_url: str | None
    photo_url: str | None  # platforms only
    icon_url: str | None  # platforms only
