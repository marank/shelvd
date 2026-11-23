"""URL configuration: the API under /api/, the admin only if ADMIN_ENABLED."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, URLResolver, path

from .api import urlpatterns as api_urlpatterns  # everything under /api/

urlpatterns: list[URLPattern | URLResolver] = [*api_urlpatterns]

# Defense in depth: nginx also answers /admin with 404 when ADMIN_ENABLED is false.
if settings.ADMIN_ENABLED:
    urlpatterns.insert(0, path("admin/", admin.site.urls))

# Covers in native development; in Docker nginx serves /media/ from DATA_DIR.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
