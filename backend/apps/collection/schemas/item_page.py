from ninja import Schema

from .item import ItemOut
from .tree import SectionOut


class ItemPageOut(Schema):
    """A page of items; with `section` also all headings of the whole list."""

    count: int
    items: list[ItemOut]
    sections: list[SectionOut]
