from django.contrib import admin

from ..models import Item, Loan


class LoanInline(admin.TabularInline[Loan, Item]):
    model = Loan
    extra = 0


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin[Item]):
    list_display = ["__str__", "library", "format", "status", "location", "owner"]
    list_filter = ["library", "format", "status", "release__platform"]
    search_fields = ["release__work__title", "release__title", "notes"]
    raw_id_fields = ["release"]
    inlines = [LoanInline]
