from ninja import Schema


class ErrorOut(Schema):
    """Shape of every error response ({"detail": "..."}), as Ninja's HttpError renders it."""

    detail: str
