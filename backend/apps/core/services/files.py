"""Removing stored files together with the rows that point at them."""

from __future__ import annotations

from collections.abc import Iterable

from django.core.files.storage import Storage
from django.db import transaction
from django.db.models.fields.files import FieldFile


def delete_files_on_commit(files: Iterable[FieldFile]) -> None:
    """Delete these files from their storage once the current transaction commits, so a
    rollback keeps rows and files together. Empty fields are skipped."""
    stored = [(file.storage, file.name) for file in files if file.name]
    if stored:
        transaction.on_commit(lambda: _delete(stored))


def _delete(stored: list[tuple[Storage, str]]) -> None:
    for storage, name in stored:
        storage.delete(name)
