from uuid import UUID

from ninja import Schema


class OwnedReleaseOut(Schema):
    release_id: UUID
    work_id: UUID
    copies: int  # owned (not sold) copies of this release in the library
