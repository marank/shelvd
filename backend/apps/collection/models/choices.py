from django.db import models
from django.utils.translation import gettext_lazy as _


class ViewerLoans(models.TextChoices):
    """What a library's viewers see of loans."""

    HIDDEN = "hidden", _("nothing")
    STATUS = "status", _("only whether a copy is lent")


class Role(models.TextChoices):
    """What a member may do in a library. The owner can always do everything."""

    VIEWER = "viewer"
    EDITOR = "editor"


class ItemFormat(models.TextChoices):
    PHYSICAL = "physical"
    DIGITAL = "digital"


class ItemStatus(models.TextChoices):
    """A copy in a library is owned (or was, once sold). Games not yet here — watched,
    pre-ordered, bought but not arrived — are tracking entries (apps.tracking)."""

    OWNED = "owned"
    SOLD = "sold"


class Condition(models.TextChoices):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


class Completeness(models.TextChoices):
    SEALED = "sealed"
    COMPLETE = "complete"  # box, game and manual
    BOX_AND_GAME = "box_and_game"
    LOOSE = "loose"  # cartridge/disc only


class PlayStatus(models.TextChoices):
    UNPLAYED = "unplayed"
    PLAYING = "playing"
    FINISHED = "finished"
    COMPLETED = "completed"  # 100 %
    ABANDONED = "abandoned"


class LocationKind(models.TextChoices):
    ROOM = "room"
    FURNITURE = "furniture"
    SHELF = "shelf"
    BOX = "box"
    OTHER = "other"


class Layout(models.TextChoices):
    GRID = "grid"
    LIST = "list"
    TABLE = "table"
