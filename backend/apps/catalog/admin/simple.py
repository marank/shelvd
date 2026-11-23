from django.contrib import admin

from ..models import Barcode, Company, Genre


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin[Company]):
    search_fields = ["name"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin[Genre]):
    search_fields = ["name"]


@admin.register(Barcode)
class BarcodeAdmin(admin.ModelAdmin[Barcode]):
    list_display = ["code", "release", "source", "confirmed_by", "created_at"]
    search_fields = ["code", "release__work__title", "release__title"]
    autocomplete_fields = ["release"]
