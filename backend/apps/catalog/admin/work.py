from django.contrib import admin

from ..models import Release, Work


class ReleaseInline(admin.TabularInline[Release, Work]):
    model = Release
    extra = 0
    fields = ["platform", "region", "title", "edition", "release_date", "publisher"]
    autocomplete_fields = ["publisher"]


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin[Work]):
    list_display = ["title", "media_type", "first_release_date"]
    list_filter = ["media_type", "genres"]
    search_fields = ["title"]
    filter_horizontal = ["genres", "developers"]
    inlines = [ReleaseInline]
