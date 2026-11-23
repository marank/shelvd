from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import UUIDModel


class User(UUIDModel, AbstractUser):
    """Custom user from day one, so the UUID primary key is in the very first migration."""

    def __str__(self) -> str:
        return self.get_username()

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"
        # "Alice" and "alice" are one account (the login backend looks names up likewise).
        constraints = [models.UniqueConstraint(Lower("username"), name="unique_username_ci")]
