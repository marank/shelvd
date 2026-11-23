from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Schema


class ReviewEntryOut(Schema):
    """One unreviewed catalog entry: a game, a release or a barcode."""

    kind: Literal["work", "release", "barcode"]
    id: UUID
    title: str  # the game's title
    detail: str  # platform and region of a release, the code of a barcode
    work_id: UUID
    release_id: UUID | None
    created_by: str | None
    created_at: datetime
    copies: int  # copies using it, in all libraries


class ReviewQueueOut(Schema):
    count: int
    entries: list[ReviewEntryOut]


class ApproveIn(Schema):
    works: list[UUID] = []
    releases: list[UUID] = []
    barcodes: list[UUID] = []


class ApprovedOut(Schema):
    approved: int
