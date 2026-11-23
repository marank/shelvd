"""OpenCritic (via RapidAPI): critic scores. Metacritic has no API, OpenCritic does.

Needs a RapidAPI key subscribed to the OpenCritic API (there is a free tier)."""

from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext as _

from ..services.integrations import Config, config
from .base import FactRecord, ProviderError

HOST = "opencritic-api.p.rapidapi.com"


class OpenCriticSource:
    name = "opencritic"

    def __init__(self, cfg: Config | None = None) -> None:
        self.cfg = cfg or config("opencritic")

    def enabled(self) -> bool:
        return self.cfg.active

    def _get(self, path: str, **params: str) -> Any:
        try:
            response = httpx.get(
                f"https://{HOST}{path}",
                params=params,
                headers={
                    "X-RapidAPI-Key": str(self.cfg.value("rapidapi_key") or ""),
                    "X-RapidAPI-Host": HOST,
                },
                timeout=settings.PROVIDER_TIMEOUT,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"OpenCritic request failed: {exc}") from exc

    def search(self, title: str) -> list[FactRecord]:
        found = self._get("/game/search", criteria=title) or []
        if not isinstance(found, list):
            raise ProviderError("OpenCritic returned an unexpected response.")
        return [
            FactRecord(
                source=self.name,
                external_id=str(g["id"]),
                title=str(g.get("name") or ""),
                url=f"https://opencritic.com/game/{g['id']}/{slugify(str(g.get('name') or ''))}",
            )
            for g in found
            if isinstance(g, dict) and g.get("id")
        ]

    def get(self, external_id: str) -> FactRecord | None:
        game = self._get(f"/game/{external_id}")
        if not isinstance(game, dict) or not game.get("id"):
            return None
        values = {
            name: round(float(game[key]), 1)
            for name, key in (("score", "topCriticScore"), ("recommended", "percentRecommended"))
            if isinstance(game.get(key), (int, float)) and game[key] >= 0
        }
        name = str(game.get("name") or "")
        released = str(game.get("firstReleaseDate") or "")[:4]
        return FactRecord(
            source=self.name,
            external_id=str(game["id"]),
            title=name,
            url=str(game.get("url") or f"https://opencritic.com/game/{game['id']}/{slugify(name)}"),
            year=int(released) if released.isdigit() else None,
            values=values,
        )

    def test(self) -> str:
        found = self.search("Zelda")
        return _("%(n)d results for “%(query)s”") % {"n": len(found), "query": "Zelda"}
