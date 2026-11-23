from django.contrib import admin

from ..models import Library, LibraryMember


class MemberInline(admin.TabularInline[LibraryMember, Library]):
    model = LibraryMember
    extra = 0


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin[Library]):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name", "owner__username"]
    inlines = [MemberInline]
