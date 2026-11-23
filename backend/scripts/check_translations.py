"""Fail when a backend text is untranslated or fuzzy.

Run after `manage.py makemessages`, which adds new strings from the code as untranslated:

    uv run python manage.py makemessages -l de --ignore=.venv
    uv run --with polib python scripts/check_translations.py

Part of `just check-backend` (and so CI).
"""

import pathlib
import sys

import polib

bad = False
for path in sorted(pathlib.Path("locale").glob("*/LC_MESSAGES/django.po")):
    po = polib.pofile(str(path))
    for entry in po.untranslated_entries():
        print(f"{path}: untranslated: {entry.msgid}")
        bad = True
    for entry in po.fuzzy_entries():
        print(f"{path}: fuzzy: {entry.msgid}")
        bad = True
print("translations incomplete" if bad else "translations complete")
sys.exit(1 if bad else 0)
