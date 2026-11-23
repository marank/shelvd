from django.contrib import admin

from ..models import Platform


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin[Platform]):
    list_display = ["name", "short_name", "manufacturer", "release_year", "media_type"]
    list_filter = ["manufacturer", "media_type"]
    search_fields = ["name", "short_name"]
    prepopulated_fields = {"slug": ["name"]}
