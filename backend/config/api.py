from django.apps import apps
from django.conf import settings
from django.urls import URLPattern, URLResolver, path
from ninja import NinjaAPI
from ninja.security import django_auth

from apps.accounts.api.auth import router as auth_router
from apps.catalog.api.catalog import router as catalog_router
from apps.catalog.api.review import router as review_router
from apps.catalog.api.terms import router as terms_router
from apps.collection.api import routers as collection_routers
from apps.collection.api.item_lookup import router as item_lookup_router
from apps.core.api.health import router as health_router
from apps.providers.api.descriptions import router as descriptions_router
from apps.providers.api.facts import router as facts_router
from apps.providers.api.integrations import router as integrations_router
from apps.providers.api.lookup import router as lookup_router
from apps.providers.api.metadata import router as metadata_router
from apps.sharing.api.lists import router as lists_router
from apps.sharing.api.public import router as public_router
from apps.tracking.api.tracking import router as tracking_router

from .addons import mount

api = NinjaAPI(
    title="shelvd API",
    auth=django_auth,  # session auth; enforces CSRF for unsafe methods
    docs_url="/docs" if settings.DEBUG else None,
    urls_namespace="api",
)
api.add_router("/health", health_router)
api.add_router("/auth", auth_router)
api.add_router("/catalog", catalog_router)
api.add_router("/catalog", review_router)
api.add_router("/catalog", terms_router)
api.add_router("/catalog", facts_router)
api.add_router("/catalog", metadata_router)
api.add_router("/catalog", descriptions_router)
api.add_router("/integrations", integrations_router)
for collection_router in collection_routers:
    api.add_router("/libraries", collection_router)
api.add_router("/items", item_lookup_router)
api.add_router("/lookup", lookup_router)
api.add_router("/lists", lists_router)
api.add_router("/public", public_router)
# Not "/tracking": content blockers (uBlock, EasyPrivacy …) block such URLs.
api.add_router("/watchlist", tracking_router)

# Add-ons (backend/addons) bring their own routers: AppConfig.api_routers.
mount(api, apps.get_app_configs())

urlpatterns: list[URLPattern | URLResolver] = [path("api/", api.urls)]
