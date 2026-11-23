"""Add-ons: optional Django apps that live outside this repository.

Each add-on is a package `addons/<name>/` (git-ignored here, copied in by the add-on's own
build) with an `AppConfig` in `apps.py`. `config/settings.py` installs every package found
here unless ADDONS_ENABLED=false. An add-on plugs in only through these seams:

- `AppConfig.api_routers`: `(prefix, "module:router")` pairs added to the API (`config/api.py`);
- `AppConfig.ready()`: `providers.services.integrations.register()` for its integrations,
  `providers.services.scheduler.register()` for periodic jobs and
  `providers.sources.registry.register_testable()` for the integrations' "Test" button.

The public OpenAPI schema (`frontend/openapi.json`) is always exported without add-ons.
"""
