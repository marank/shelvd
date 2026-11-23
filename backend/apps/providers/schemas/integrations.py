from datetime import date, datetime
from typing import Any
from uuid import UUID

from ninja import Schema


class IntegrationFieldOut(Schema):
    name: str
    type: str  # text | number | bool
    secret: bool
    required: bool
    # Plain settings: their value. Secrets: never the value, only whether one is set and
    # a masked hint ("••••1234").
    value: Any = None
    has_value: bool = False
    masked: str = ""


class IntegrationOut(Schema):
    key: str
    name: str
    kind: str  # metadata | facts | covers | playtime
    url: str
    unofficial: bool
    refreshes: bool
    enabled: bool
    # Switched on and every required field filled in.
    active: bool
    fields: list[IntegrationFieldOut]
    last_ok_at: datetime | None
    last_error: str
    last_error_at: datetime | None
    last_run_at: datetime | None


class IntegrationPatch(Schema):
    enabled: bool | None = None
    options: dict[str, Any] | None = None
    # Only the secrets sent change; "" removes one.
    secrets: dict[str, str] | None = None


class TestOut(Schema):
    ok: bool
    message: str


class FactCandidateOut(Schema):
    external_id: str
    title: str
    url: str
    year: int | None
    platforms: str
    values: dict[str, float]


class PinIn(Schema):
    external_id: str


class CoverCandidateOut(Schema):
    source: str
    title: str
    region: str
    platform: str
    width: int | None
    height: int | None
    token: str


class CoverIn(Schema):
    token: str


class MetadataCandidateOut(Schema):
    external_id: str
    title: str
    year: int | None
    platforms: list[str]
    summary: str
    cover_url: str


class MetadataValueOut(Schema):
    text: str
    date: date | None
    precision: str | None
    image: str | None


class MetadataChangeOut(Schema):
    id: str
    field: str
    # fill: was empty · precise: a more exact date · differs: replaces what's there
    kind: str
    suggested: bool
    release_id: UUID | None
    current: MetadataValueOut
    proposed: MetadataValueOut


class MetadataPreviewOut(Schema):
    external_id: str
    title: str
    changes: list[MetadataChangeOut]


class MetadataApplyIn(Schema):
    external_id: str
    changes: list[str]


class MetadataApplyOut(Schema):
    applied: list[str]
