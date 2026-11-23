"""Stand-ins for httpx responses, so tests never touch the network."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx


def response(
    status: int = 200, json: Any = None, content: bytes = b"", ctype: str = ""
) -> httpx.Response:
    request = httpx.Request("GET", "https://example.invalid")
    if json is not None:
        return httpx.Response(status, json=json, request=request)
    return httpx.Response(status, content=content, headers={"content-type": ctype}, request=request)


def router(routes: dict[str, Callable[..., httpx.Response]]) -> Callable[..., httpx.Response]:
    """Pick the fake by URL prefix; unknown URLs fail like a network error."""

    def call(url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        for prefix, handler in routes.items():
            if url.startswith(prefix):
                return handler(url, *args, **kwargs)
        raise httpx.ConnectError(f"no fake for {url}")

    return call


IGDB_GAME = {
    "id": 26758,
    "name": "Super Mario Odyssey",
    "summary": "Cappy!",
    "first_release_date": 1509062400,
    "cover": {"image_id": "co1mxf"},
    "genres": [{"name": "Platform"}, {"name": "Adventure"}],
    "involved_companies": [
        {"company": {"name": "Nintendo EPD"}, "developer": True, "publisher": False},
        {"company": {"name": "Nintendo"}, "developer": False, "publisher": True},
    ],
    "platforms": [{"id": 130, "name": "Nintendo Switch"}, {"id": 999, "name": "Toaster"}],
    "release_dates": [
        {"platform": 130, "date": 1509062400, "release_region": 2},
        {"platform": 130, "date": 1509062400, "release_region": 1},
    ],
}
