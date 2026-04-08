from django.contrib import admin

from app.api.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "rule_id", "device_id", "severity", "status", "timestamp")
    list_filter = ("severity", "status")
    search_fields = ("message", "rule_name", "device_serial")
    ordering = ("-timestamp", "-id")
