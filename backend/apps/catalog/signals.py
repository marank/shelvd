"""Signals for code outside the catalog that keeps references to catalog entries."""

from django.dispatch import Signal

# A game is merged into another or loses its last release to it, right before `source`
# is deleted: rows that point at `source` (e.g. an add-on's play records) move to
# `target`. Sent with sender=Work and the keyword arguments source and target.
work_merged = Signal()
