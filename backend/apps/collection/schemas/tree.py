from __future__ import annotations

from decimal import Decimal

from ninja import Schema


class GroupNodeOut(Schema):
    field: str
    key: str  # "none" for items without a value
    label: str
    count: int
    value: Decimal  # sum of the copies' current values
    children: list[GroupNodeOut]


class TreeOut(Schema):
    total: int
    total_value: Decimal
    group_by: list[str]
    nodes: list[GroupNodeOut]


class SectionOut(Schema):
    field: str
    key: str  # "none" for items without a value
    label: str
    count: int
    value: Decimal
    start: int  # index of its first row in the whole list
