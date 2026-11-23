"""Integrations: which external services exist, what they need, and their settings.

Admins configure them in the app (no .env): `DEFINITIONS` lists every service with its
fields; `config(key)` reads one (defaults filled in, secrets decrypted). Secrets are
encrypted with a key derived from SECRET_KEY – changing SECRET_KEY means entering them
again.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from ninja.errors import HttpError

from ..models import Integration

Kind = Literal["metadata", "facts", "covers", "playtime"]
FieldType = Literal["text", "number", "bool"]


@dataclass(frozen=True)
class FieldDef:
    name: str
    type: FieldType = "text"
    secret: bool = False
    default: Any = None
    required: bool = False


@dataclass(frozen=True)
class Definition:
    key: str
    name: str
    kind: Kind
    url: str
    fields: tuple[FieldDef, ...] = ()
    enabled_default: bool = False
    # Not an official API: may break any time; switched off by default.
    unofficial: bool = False
    # Shows when the data counts as old and whether the scheduler refreshes it.
    refreshes: bool = False


FRESHNESS = (
    FieldDef("max_age_hours", "number", default=720),
    FieldDef("periodic", "bool", default=False),
    FieldDef("periodic_hours", "number", default=24),
    FieldDef("batch", "number", default=20),
)

DEFINITIONS: dict[str, Definition] = {
    d.key: d
    for d in (
        Definition(
            "igdb",
            "IGDB",
            "metadata",
            "https://api-docs.igdb.com/#account-creation",
            (
                FieldDef("client_id", secret=True, required=True),
                FieldDef("client_secret", secret=True, required=True),
            ),
        ),
        Definition(
            "wikipedia",
            "Wikipedia",
            "metadata",
            "https://www.wikidata.org/wiki/Wikidata:Data_access",
        ),
        Definition(
            "hltb",
            "HowLongToBeat",
            "facts",
            "https://howlongtobeat.com",
            FRESHNESS,
            unofficial=True,
            refreshes=True,
        ),
        Definition(
            "opencritic",
            "OpenCritic",
            "facts",
            "https://rapidapi.com/opencritic-opencritic-default/api/opencritic-api",
            (FieldDef("rapidapi_key", secret=True, required=True), *FRESHNESS),
            refreshes=True,
        ),
        Definition(
            "thegamesdb",
            "TheGamesDB",
            "covers",
            "https://api.thegamesdb.net/key.php",
            (FieldDef("api_key", secret=True, required=True),),
        ),
        Definition(
            "screenscraper",
            "ScreenScraper",
            "covers",
            "https://www.screenscraper.fr/membreinscription.php",
            (
                # Optional: a user account is enough to try; ScreenScraper says when a
                # request also needs developer credentials.
                FieldDef("dev_id", secret=True),
                FieldDef("dev_password", secret=True),
                FieldDef("user", required=True),
                FieldDef("password", secret=True, required=True),
            ),
        ),
    )
}


def register(definition: Definition) -> None:
    """An add-on's integration (AppConfig.ready, see backend/addons/__init__.py)."""
    DEFINITIONS[definition.key] = definition


def _fernet() -> Fernet:
    digest = hashlib.sha256(f"shelvd-integrations:{settings.SECRET_KEY}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str | None:
    """None when the token wasn't made with the current SECRET_KEY."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken, ValueError:
        return None


def _secrets(row: Integration | None) -> dict[str, str]:
    if row is None or not row.secrets:
        return {}
    raw = decrypt(row.secrets)
    return json.loads(raw) if raw else {}


@dataclass
class Config:
    key: str
    enabled: bool
    options: dict[str, Any]
    secrets: dict[str, str]
    row: Integration | None = field(default=None, repr=False)

    def value(self, name: str) -> Any:
        return self.secrets.get(name) or self.options.get(name)

    @property
    def complete(self) -> bool:
        """All required fields are filled in."""
        return all(self.value(f.name) for f in DEFINITIONS[self.key].fields if f.required)

    @property
    def active(self) -> bool:
        return self.enabled and self.complete


def definition(key: str) -> Definition:
    if key not in DEFINITIONS:
        raise HttpError(404, _("Unknown integration."))
    return DEFINITIONS[key]


def config(key: str) -> Config:
    d = definition(key)
    row = Integration.objects.filter(key=key).first()
    options = {f.name: f.default for f in d.fields if not f.secret}
    options.update((row.options if row else {}) or {})
    return Config(
        key=key,
        enabled=row.enabled if row else d.enabled_default,
        options=options,
        secrets=_secrets(row),
        row=row,
    )


def save(
    key: str,
    enabled: bool | None = None,
    options: dict[str, Any] | None = None,
    secrets: dict[str, str] | None = None,
) -> Config:
    """Secrets are merged: only the ones sent change; an empty string removes one."""
    d = definition(key)
    row, _created = Integration.objects.get_or_create(
        key=key, defaults={"enabled": d.enabled_default}
    )
    fields = {f.name: f for f in d.fields}
    if enabled is not None:
        row.enabled = enabled
    if options is not None:
        row.options = {**row.options, **_clean_options(fields, options)}
    if secrets is not None:
        current = _merge_secrets(fields, _secrets(row), secrets)
        row.secrets = encrypt(json.dumps(current)) if current else ""
    row.save()
    return config(key)


def _field(fields: dict[str, FieldDef], name: str, *, secret: bool) -> FieldDef:
    """The definition of a setting sent as an option (secret=False) or a secret."""
    f = fields.get(name)
    if f is None or f.secret != secret:
        raise HttpError(400, _("Unknown setting: %(name)s") % {"name": name})
    return f


def _clean_options(fields: dict[str, FieldDef], options: dict[str, Any]) -> dict[str, Any]:
    return {name: _coerce(_field(fields, name, secret=False), v) for name, v in options.items()}


def _merge_secrets(
    fields: dict[str, FieldDef], current: dict[str, str], sent: dict[str, str]
) -> dict[str, str]:
    """Only the secrets sent change; an empty string removes one."""
    merged = dict(current)
    for name, value in sent.items():
        _field(fields, name, secret=True)
        if value:
            merged[name] = value.strip()
        else:
            merged.pop(name, None)
    return merged


def _coerce(f: FieldDef, value: Any) -> Any:
    if f.type == "bool":
        return bool(value)
    if f.type == "number":
        try:
            number = int(value)
        except TypeError, ValueError:
            raise HttpError(400, _("%(name)s must be a number.") % {"name": f.name}) from None
        if number < 0:
            raise HttpError(400, _("%(name)s must be a number.") % {"name": f.name})
        return number
    return str(value or "").strip()


def mask(value: str) -> str:
    """What the UI shows of a stored secret: just enough to recognize it."""
    return "••••" + value[-4:] if len(value) > 8 else "••••"


def record_ok(key: str) -> None:
    Integration.objects.filter(key=key).update(last_ok_at=timezone.now())


def record_error(key: str, message: str) -> None:
    row, _created = Integration.objects.get_or_create(
        key=key, defaults={"enabled": DEFINITIONS[key].enabled_default}
    )
    row.last_error = message[:500]
    row.last_error_at = timezone.now()
    row.save(update_fields=["last_error", "last_error_at", "updated_at"])
