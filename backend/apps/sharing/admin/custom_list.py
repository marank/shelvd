from django.contrib import admin

from ..models import CustomList, ListEntry


class EntryInline(admin.TabularInline[ListEntry, CustomList]):
    model = ListEntry
    extra = 0
    raw_id_fields = ["release", "item"]


@admin.register(CustomList)
class CustomListAdmin(admin.ModelAdmin[CustomList]):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name"]
    inlines = [EntryInline]
