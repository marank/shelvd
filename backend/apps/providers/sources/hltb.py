"""HowLongToBeat: how long a game takes (main story, + extras, completionist).

There is no official API. Searching uses the site's own search like its pages do: a short-
lived token from /api/search/site/init, sent as x-auth-token to /api/search/site (a 403 means
the token expired: fetch a new one and retry once). A single game is read from its page's
embedded data. The site changes now and then, so treat this as best effort: the integration
is off by default and its results are cached (catalog.WorkFact).
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _

from ..services.integrations import Config, config
from .base import FactRecord, ProviderError

BASE = "https://howlongtobeat.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36",
    "Referer": f"{BASE}/",
    "Origin": BASE,
}
INIT = f"{BASE}/api/search/site/init"
SEARCH = f"{BASE}/api/search/site"
TOKEN_CACHE = "providers:hltb:token"  # noqa: S105  cache key name, not a secret
TOKEN_SECONDS = 600
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)


def _hours(seconds: Any) -> float | None:
    try:
        value = float(seconds)
    except TypeError, ValueError:
        return None
    return round(value / 3600, 1) if value > 0 else None


class HLTBSource:
    name = "hltb"

    def __init__(self, cfg: Config | None = None) -> None:
        self.cfg = cfg or config("hltb")

    def enabled(self) -> bool:
        return self.cfg.active

    def _get(self, url: str) -> str:
        try:
            response = httpx.get(url, headers=HEADERS, timeout=settings.PROVIDER_TIMEOUT)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"HowLongToBeat request failed: {exc}") from exc
        return response.text

    def _token(self, *, fresh: bool = False) -> str:
        cached = None if fresh else cache.get(TOKEN_CACHE)
        if isinstance(cached, str):
            return cached
        try:
            response = httpx.get(
                INIT,
                params={"t": int(time.time() * 1000)},
                headers=HEADERS,
                timeout=settings.PROVIDER_TIMEOUT,
            )
            response.raise_for_status()
            token = response.json().get("token")
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise ProviderError(f"HowLongToBeat search init failed: {exc}") from exc
        if not isinstance(token, str) or not token:
            raise ProviderError("HowLongToBeat changed its site: no search token.")
        cache.set(TOKEN_CACHE, token, TOKEN_SECONDS)
        return token

    def _record(self, game: dict[str, Any]) -> FactRecord:
        values = {
            name: hours
            for name, key in (
                ("main", "comp_main"),
                ("extra", "comp_plus"),
                ("complete", "comp_100"),
            )
            if (hours := _hours(game.get(key))) is not None
        }
        year = game.get("release_world")
        return FactRecord(
            source=self.name,
            external_id=str(game["game_id"]),
            title=str(game.get("game_name") or ""),
            url=f"{BASE}/game/{game['game_id']}",
            year=int(year) if isinstance(year, int) and year > 0 else None,
            platforms=str(game.get("profile_platform") or ""),
            values=values,
        )

    def search(self, title: str) -> list[FactRecord]:
        body = {
            "searchType": "games",
            "searchTerms": title.split(),
            "searchPage": 1,
            "size": 20,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": None, "max": None},
                    "gameplay": {"perspective": "", "flow": "", "genre": "", "difficulty": ""},
                    "rangeYear": {"min": "", "max": ""},
                    "modifier": "",
                },
                "users": {"sortCategory": "postcount"},
                "lists": {"sortCategory": "follows"},
                "filter": "",
                "sort": 0,
                "randomizer": 0,
            },
            "useCache": True,
        }

        def post(*, fresh: bool) -> httpx.Response:
            return httpx.post(
                SEARCH,
                json=body,
                headers={**HEADERS, "x-auth-token": self._token(fresh=fresh)},
                timeout=settings.PROVIDER_TIMEOUT,
            )

        try:
            response = post(fresh=False)
            if response.status_code == 403:
                # The token expired – once more with a fresh one.
                response = post(fresh=True)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"HowLongToBeat search failed: {exc}") from exc
        games = data.get("data") if isinstance(data, dict) else None
        if not isinstance(games, list):
            raise ProviderError("HowLongToBeat returned an unexpected response.")
        return [self._record(g) for g in games if isinstance(g, dict) and g.get("game_id")]

    def get(self, external_id: str) -> FactRecord | None:
        if not external_id.isdigit():
            return None
        found = NEXT_DATA.search(self._get(f"{BASE}/game/{external_id}"))
        try:
            data = json.loads(found.group(1)) if found else {}
            game = data["props"]["pageProps"]["game"]["data"]["game"][0]
        except ValueError, KeyError, IndexError, TypeError:
            return None
        return self._record(game)

    def test(self) -> str:
        found = self.search("Super Mario Odyssey")
        return _("%(n)d results for “%(query)s”") % {
            "n": len(found),
            "query": "Super Mario Odyssey",
        }
