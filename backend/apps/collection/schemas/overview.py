from typing import Literal
from uuid import UUID

from ninja import Schema

from ..models import Layout


class OverviewOut(Schema):
    id: UUID
    name: str
    group_by: list[str]
    section: str
    filters: list[str]
    match: Literal["all", "any"]
    fields: dict[str, list[str]]
    sort: str
    layout: Layout
    position: int


class OverviewIn(Schema):
    name: str
    group_by: list[str] = []
    section: str = ""
    filters: list[str] = []
    match: Literal["all", "any"] = "all"
    fields: dict[str, list[str]] = {}
    sort: str = "game.title"
    layout: Layout = Layout.GRID
    position: int = 0


class OverviewPatch(Schema):
    name: str | None = None
    group_by: list[str] | None = None
    section: str | None = None
    filters: list[str] | None = None
    match: Literal["all", "any"] | None = None
    fields: dict[str, list[str]] | None = None
    sort: str | None = None
    layout: Layout | None = None
    position: int | None = None
