from django.contrib import admin

from ..models import Tracking


@admin.register(Tracking)
class TrackingAdmin(admin.ModelAdmin[Tracking]):
    list_display = ["release", "user", "status", "library", "ordered_on"]
    list_filter = ["status"]
    raw_id_fields = ["release"]
