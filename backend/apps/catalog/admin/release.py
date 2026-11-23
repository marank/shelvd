from django.contrib import admin

from ..models import Release


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin[Release]):
    list_display = ["__str__", "platform", "region", "release_date", "publisher"]
    list_filter = ["platform", "region"]
    search_fields = ["work__title", "title", "barcodes__code"]
    autocomplete_fields = ["work", "publisher", "developers"]
