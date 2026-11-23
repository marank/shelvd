from django.contrib import admin

from ..models import Location, Overview, Person


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin[Location]):
    list_display = ["__str__", "library", "kind"]
    list_filter = ["library", "kind"]
    search_fields = ["name"]


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin[Person]):
    list_display = ["name", "library", "email", "user"]
    search_fields = ["name", "email"]


@admin.register(Overview)
class OverviewAdmin(admin.ModelAdmin[Overview]):
    list_display = ["name", "library", "user", "position"]
