"""ScreenScraper: very good regional box art, especially for handhelds and retro.

Needs a user account, whose level sets the daily quota. Developer credentials (requested
from ScreenScraper per software) are optional: sent only when configured. Image URLs
carry the credentials, so they never reach the browser: previews and downloads go
through our server (services.covers)."""

from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings
from django.utils.translation import gettext as _

from ..services.integrations import Config, config
from .base import CoverRecord, ProviderError

API = "https://api.screenscraper.fr/api2"
# ScreenScraper system ids → our platform slugs (to label and rank results).
SYSTEMS = {
    135: "pc", 32: "xbox", 33: "xbox-360", 3: "nes", 9: "game-boy", 4: "snes", 14: "n64",
    10: "game-boy-color", 12: "game-boy-advance", 13: "gamecube", 15: "nds", 16: "wii",
    17: "3ds", 18: "wii-u", 225: "switch", 2: "master-system", 1: "mega-drive",
    21: "game-gear", 22: "saturn", 23: "dreamcast", 57: "ps1", 58: "ps2", 61: "psp",
    59: "ps3", 62: "ps-vita", 60: "ps4",
}  # fmt: skip
# ScreenScraper is often busy and slow to answer a search: give it longer than the others
# (still well below gunicorn's 30 s worker timeout).
READ_TIMEOUT = 20.0
REGIONS = {"eu": "pal", "us": "na", "jp": "jp", "wor": "", "de": "pal", "fr": "pal", "uk": "pal"}


def _error_message(response: httpx.Response) -> str:
    text = response.text.lower()
    if "identifiants développeur" in text:
        return _(
            "ScreenScraper wants developer credentials for this. Request them in the "
            "ScreenScraper forum and enter them here."
        )
    if "identifiants utilisateurs" in text:
        return _("ScreenScraper doesn't accept the user name or password.")
    if response.is_error:
        return _("ScreenScraper request failed (HTTP %(status)s).") % {
            "status": response.status_code
        }
    return _("ScreenScraper returned an unexpected response.")


class ScreenScraperSource:
    name = "screenscraper"
    hosts: tuple[str, ...] = (
        "screenscraper.fr",
        "www.screenscraper.fr",
        "neoclone.screenscraper.fr",
    )
    # Often takes many seconds and has a daily quota: only asked when someone searches.
    automatic = False

    def __init__(self, cfg: Config | None = None) -> None:
        self.cfg = cfg or config("screenscraper")

    def enabled(self) -> bool:
        return self.cfg.active

    def _get(self, endpoint: str, **params: str) -> dict[str, Any]:
        auth = {
            "ssid": str(self.cfg.value("user") or ""),
            "sspassword": str(self.cfg.value("password") or ""),
            "softname": "shelvd",
            "output": "json",
        }
        dev_id, dev_password = self.cfg.value("dev_id"), self.cfg.value("dev_password")
        if dev_id and dev_password:
            auth |= {"devid": str(dev_id), "devpassword": str(dev_password)}
        try:
            response = httpx.get(
                f"{API}/{endpoint}",
                params={**auth, **params},
                timeout=httpx.Timeout(
                    settings.PROVIDER_TIMEOUT, read=max(READ_TIMEOUT, settings.PROVIDER_TIMEOUT)
                ),
            )
        except httpx.TimeoutException as exc:
            raise ProviderError(
                _("ScreenScraper did not answer in time – it is often busy. Try again later.")
            ) from exc
        except httpx.HTTPError as exc:
            # Never put the URL (with credentials) into the message.
            raise ProviderError(f"ScreenScraper request failed ({type(exc).__name__}).") from exc
        try:
            data = response.json()
        except ValueError:
            data = None
        result = data.get("response") if isinstance(data, dict) else None
        if response.is_error or not isinstance(result, dict):
            # Errors come back as short French text (it never echoes the credentials).
            raise ProviderError(_error_message(response))
        return result

    def covers(self, title: str, platform_slug: str = "") -> list[CoverRecord]:
        found = [
            cover
            for game in self._get("jeuRecherche.php", recherche=title).get("jeux") or []
            if isinstance(game, dict) and game.get("id")
            for cover in self._game_covers(game)
        ]
        return sorted(found, key=lambda c: c.platform != platform_slug)

    def _game_covers(self, game: dict[str, Any]) -> list[CoverRecord]:
        """The 2D box arts of one search result."""
        names = game.get("noms") or []
        name = next((n.get("text") for n in names if isinstance(n, dict)), "") or ""
        slug = SYSTEMS.get(int((game.get("systeme") or {}).get("id") or 0), "")
        return [
            CoverRecord(
                source=self.name,
                url=str(media["url"]),
                title=str(name),
                region=REGIONS.get(str(media.get("region") or ""), ""),
                platform=slug,
            )
            for media in game.get("medias") or []
            if media.get("type") == "box-2D" and media.get("url")
        ]

    def test(self) -> str:
        user = self._get("ssuserInfos.php").get("ssuser") or {}
        requests = user.get("requeststoday")
        limit = user.get("maxrequestsperday")
        if not limit:
            return _("OK")
        return _("OK – %(used)s/%(limit)s requests today") % {"used": requests, "limit": limit}
