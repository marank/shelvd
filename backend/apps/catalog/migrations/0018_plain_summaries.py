"""Imports left HTML in game descriptions (<b>, lists): turn them into plain text.

The cleaning is copied here (not imported) so this migration keeps doing the same later."""

import html
import re

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

BREAKS = [
    (re.compile(r"<\s*br\s*/?\s*>", re.I), "\n"),
    (re.compile(r"<\s*/?\s*p\b[^>]*>", re.I), "\n\n"),
    (re.compile(r"<\s*li\b[^>]*>", re.I), "\n• "),
    (re.compile(r"<\s*/?\s*(?:ul|ol)\b[^>]*>", re.I), "\n\n"),
]
TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def plain_text(text: str) -> str:
    if "<" not in text and "&" not in text:
        return text.strip()
    for pattern, replacement in BREAKS:
        text = pattern.sub(replacement, text)
    text = html.unescape(TAG.sub("", text))
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return re.sub(r"(^• .*)\n\n(?=• )", r"\1\n", text, flags=re.M).strip()


def clean(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Work = apps.get_model("catalog", "Work")
    for work in Work.objects.filter(summary__regex=r"<[a-zA-Z/]|&[a-zA-Z#0-9]+;").only("summary"):
        cleaned = plain_text(work.summary)
        if cleaned != work.summary:
            work.summary = cleaned
            work.save(update_fields=["summary"])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0017_term_descriptions")]

    operations = [migrations.RunPython(clean, migrations.RunPython.noop)]
