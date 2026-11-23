import uuid

from django.db import models

# UUIDv7 (time-ordered, index friendly) where the Python version provides it.
uuid_default = getattr(uuid, "uuid7", uuid.uuid4)


class UUIDModel(models.Model):
    """Base for every model in this project: UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid_default, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(UUIDModel):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
