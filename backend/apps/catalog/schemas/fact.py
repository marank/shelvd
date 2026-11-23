from datetime import datetime

from ninja import Schema


class FactOut(Schema):
    """A cached fact of a game from one source (HowLongToBeat, OpenCritic …)."""

    source: str
    title: str
    url: str
    values: dict[str, float]
    status: str
    pinned: bool
    fetched_at: datetime | None
