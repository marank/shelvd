"""TheGamesDB: box art (front covers), also regional ones. Needs a free API key."""

from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings
from django.utils.translation import gettext as _

from ..services.integrations import Config, config
from .base import CoverRecord, ProviderError

API = "https://api.thegamesdb.net/v1.1"
# TheGamesDB platform ids → our platform slugs (to label and rank results).
PLATFORMS = {
    1: "pc", 14: "xbox", 15: "xbox-360", 4920: "xbox-one", 4981: "xbox-series", 7: "nes",
    4: "game-boy", 6: "snes", 3: "n64", 41: "game-boy-color", 5: "game-boy-advance",
    2: "gamecube", 8: "nds", 9: "wii", 4912: "3ds", 38: "wii-u", 4971: "switch",
    35: "master-system", 36: "mega-drive", 20: "game-gear", 17: "saturn", 16: "dreamcast",
    10: "ps1", 11: "ps2", 13: "psp", 12: "ps3", 39: "ps-vita", 4919: "ps4", 4980: "ps5",
}  # fmt: skip
REGIONS = {1: "ntsc", 2: "na", 3: "ntsc", 4: "jp", 5: "kr", 6: "pal", 7: "pal", 8: "pal"}


class TheGamesDBSource:
    name = "thegamesdb"
    hosts: tuple[str, ...] = ("cdn.thegamesdb.net",)
    automatic = True

    def __init__(self, cfg: Config | None = None) -> None:
        self.cfg = cfg or config("thegamesdb")

    def enabled(self) -> bool:
        return self.cfg.active

    def _get(self, path: str, **params: str) -> dict[str, Any]:
        try:
            response = httpx.get(
                f"{API}{path}",
                params={"apikey": str(self.cfg.value("api_key") or ""), **params},
                timeout=settings.PROVIDER_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Not str(exc): an HTTP error quotes the URL, and that carries the API key.
            detail = (
                f"HTTP {exc.response.status_code}"
                if isinstance(exc, httpx.HTTPStatusError)
                else type(exc).__name__
            )
            raise ProviderError(f"TheGamesDB request failed ({detail}).") from exc
        if not isinstance(data, dict):
            raise ProviderError("TheGamesDB returned an unexpected response.")
        return data

    def covers(self, title: str, platform_slug: str = "") -> list[CoverRecord]:
        data = self._get("/Games/ByGameName", name=title, fields="region_id", include="boxart")
        games = (data.get("data") or {}).get("games") or []
        boxart = (data.get("include") or {}).get("boxart") or {}
        base = ((boxart.get("base_url") or {}).get("original") or "").rstrip("/")
        images = boxart.get("data") or {}
        found = [
            self._cover(game, image, base)
            for game in games
            for image in images.get(str(game.get("id")), [])
            if image.get("side") == "front" and image.get("filename") and base
        ]
        # Covers for the release's own platform first.
        return sorted(found, key=lambda c: c.platform != platform_slug)

    def _cover(self, game: dict[str, Any], image: dict[str, Any], base: str) -> CoverRecord:
        """One front box art of a game; `base` is the address the file names follow."""
        width, _, height = str(image.get("resolution") or "").partition("x")
        return CoverRecord(
            source=self.name,
            url=f"{base}/{image['filename']}",
            title=str(game.get("game_title") or ""),
            region=REGIONS.get(game.get("region_id", 0), ""),
            platform=PLATFORMS.get(game.get("platform", 0), ""),
            width=int(width) if width.isdigit() else None,
            height=int(height) if height.isdigit() else None,
        )

    def test(self) -> str:
        data = self._get("/Games/ByGameName", name="Zelda")
        remaining = data.get("remaining_monthly_allowance")
        if remaining is None:
            return _("OK")
        return _("OK – %(n)s requests left this month") % {"n": remaining}
