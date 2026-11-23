from uuid import UUID

from ninja import Schema


class MoveReleaseIn(Schema):
    """Target game, or none to make the release a game of its own (with `title`)."""

    work_id: UUID | None = None
    title: str = ""


class MergeWorkIn(Schema):
    target_id: UUID


class WorkSummaryOut(Schema):
    id: UUID
    title: str
    platforms: list[str]
    releases: int
    cover_url: str | None
