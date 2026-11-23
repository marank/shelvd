"""Fail when a platform the project runs on is near the end of its security support.

    uv run python scripts/check_eol.py            (in backend/; `just check-eol`)

Dependabot ignores some major updates on purpose (PostgreSQL needs a dump and restore,
@types/node follows the Node version developers run) and offers no others for the base
images' majors. This check is what makes those upgrades come up in time: it reads the
versions from the repository and asks endoflife.date when their support ends. The weekly
CI run fails WARN_DAYS before that date, so the upgrade can be planned, not rushed.
Not part of `just check`: it needs the network and its result changes with the date.
"""

import json
import re
import sys
import tomllib
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = "https://endoflife.date/api/v1/products/{product}"
WARN_DAYS = 180


@dataclass(frozen=True)
class Platform:
    label: str
    product: str  # endoflife.date product
    cycle: str  # release cycle as endoflife.date names it ("18", "3.15", "6.1")
    source: str  # where the version comes from, for the message


def _match(path: Path, pattern: str) -> str:
    found = re.findall(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    if not found:
        raise SystemExit(f"{path.relative_to(ROOT)}: no match for {pattern!r}")
    return str(found[-1])  # the last stage of the Dockerfile is the runtime


def _django_cycle() -> str:
    lock = tomllib.loads((ROOT / "backend" / "uv.lock").read_text(encoding="utf-8"))
    version = next(p["version"] for p in lock["package"] if p["name"] == "django")
    return ".".join(str(version).split(".")[:2])


def platforms() -> list[Platform]:
    dockerfile = ROOT / "Dockerfile"
    return [
        Platform("Python", "python", _match(dockerfile, r"^FROM python:(\d+\.\d+)-"), "Dockerfile"),
        Platform(
            "Debian", "debian", _match(dockerfile, r"^FROM python:[\d.]+-slim-(\w+)"), "Dockerfile"
        ),
        Platform("Node.js", "nodejs", _match(dockerfile, r"^FROM node:(\d+)-"), "Dockerfile"),
        Platform(
            "PostgreSQL",
            "postgresql",
            _match(ROOT / "compose.yml", r"image: postgres:(\d+)"),
            "compose.yml",
        ),
        Platform("Django", "django", _django_cycle(), "backend/uv.lock"),
    ]


def releases(product: str) -> list[dict[str, object]]:
    # S310: the URL is the fixed https address above, never a file: or custom scheme.
    url = API.format(product=product)
    request = urllib.request.Request(url, headers={"User-Agent": "check-eol"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        data: dict[str, dict[str, list[dict[str, object]]]] = json.load(response)
    return data["result"]["releases"]


def find(all_releases: list[dict[str, object]], cycle: str) -> dict[str, object]:
    for release in all_releases:
        # Debian is named by codename in the image tag (trixie), the others by number.
        if cycle in (release["name"], str(release.get("codename") or "").lower()):
            return release
    raise SystemExit(f"endoflife.date knows no release {cycle!r}")


def check(platform: Platform, today: date) -> bool:
    """Print one line; False when support ends within WARN_DAYS (or has ended)."""
    all_releases = releases(platform.product)
    release = find(all_releases, platform.cycle)
    newest = all_releases[0]["name"]
    newer = f", newest {newest}" if newest != release["name"] else ""
    eol = release.get("eolFrom")
    if not isinstance(eol, str):
        print(f"ok    {platform.label} {release['name']} ({platform.source}): no end date{newer}")
        return True
    left = (date.fromisoformat(eol) - today).days
    ok = left > WARN_DAYS
    status = "ok  " if ok else "FAIL"
    name = f"{platform.label} {release['name']} ({platform.source})"
    print(f"{status}  {name}: support ends {eol}, {left} days{newer}")
    return ok


def main() -> int:
    today = datetime.now(UTC).date()
    results = [check(platform, today) for platform in platforms()]
    if all(results):
        return 0
    print(
        f"\nUpgrade what is marked FAIL: its security support ends within {WARN_DAYS} days.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
