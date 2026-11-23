"""Small helpers to read configuration from the environment.

Kept separate from settings.py so settings stays declarative. Values come from
the process environment; for native development `.env` in the repo root (or in
backend/) is loaded first, without overriding variables that are already set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def load_dotenv(*candidates: Path) -> None:
    """Minimal .env loader (KEY=VALUE, '#' comments). Existing env vars win."""
    for path in candidates:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().removeprefix("export ").strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key, value)
        return


def env_str(name: str, default: str | None = None) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        if default is None:
            raise ImproperlyConfigured(f"Environment variable {name} is required.")
        return default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean (true/false), got {value!r}.")


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer, got {value!r}.") from exc


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class AppUrl:
    scheme: str
    hostname: str
    origin: str  # scheme://host[:port], as browsers send it in the Origin header


def parse_app_urls(urls: list[str]) -> list[AppUrl]:
    parsed: list[AppUrl] = []
    for url in urls:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ImproperlyConfigured(
                f"APP_URLS entry {url!r} must look like https://host[:port]."
            )
        default_port = 443 if parts.scheme == "https" else 80
        netloc = (
            parts.hostname
            if parts.port in (None, default_port)
            else f"{parts.hostname}:{parts.port}"
        )
        parsed.append(AppUrl(parts.scheme, parts.hostname, f"{parts.scheme}://{netloc}"))
    if not parsed:
        raise ImproperlyConfigured("APP_URLS must contain at least one URL.")
    return parsed


INSECURE_SECRET_VALUES = {"", "change-me", "changeme", "secret"}


def secret_key(debug: bool) -> str:
    """Refuse to start with a weak SECRET_KEY, except for local DEBUG runs."""
    value = os.environ.get("SECRET_KEY", "")
    if value not in INSECURE_SECRET_VALUES and len(value) >= 40:
        return value
    if debug:
        # Stable, obviously-insecure key so dev sessions survive restarts.
        return "django-insecure-dev-only-" + "x" * 40
    raise ImproperlyConfigured(
        "SECRET_KEY must be a random string of at least 40 characters. Generate one with:\n"
        '  python3 -c "import secrets; print(secrets.token_urlsafe(50))"'
    )
