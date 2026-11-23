from ninja import Router

from . import items, libraries, loans, locations, overviews, owned, people

# All mounted under /api/libraries; each module owns its sub-paths.
routers: list[Router] = [
    module.router for module in (libraries, items, locations, people, loans, overviews, owned)
]

__all__ = ["routers"]
