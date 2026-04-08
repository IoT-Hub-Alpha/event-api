from django.core.exceptions import ValidationError
from django.db import models


def validate_execution_results(value):
    if not isinstance(value, list):
        raise ValidationError("execution_results must be a list of execution items")

    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("Each execution result must be a dictionary")

        if "type" not in item:
            raise ValidationError("Each execution result must have a 'type' field")

        if "status" not in item:
            raise ValidationError("Each execution result must have a 'status' field")

        action_type = item.get("type")
        allowed_types = {"notification", "stop_machine", "alert", "webhook", "command"}
        if action_type not in allowed_types:
            raise ValidationError(
                "Unsupported execution result type. Allowed values: "
                "notification, stop_machine, alert, webhook, command"
            )


def validate_telemetry_snapshot(value):
    if value is None:
        return

    if not isinstance(value, dict):
        raise ValidationError("Telemetry snapshot must be a JSON object")


class Event(models.Model):
    class EventSeverity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        WARNING = "warning", "Warning"
        INFO = "info", "Info"

    class EventStatus(models.TextChoices):
        NEW = "new", "New"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    id = models.BigAutoField(primary_key=True)
    rule_id = models.UUIDField()
    device_id = models.UUIDField()
    rule_name = models.CharField(max_length=255, blank=True, default="")
    device_serial = models.CharField(max_length=100, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=20, choices=EventSeverity.choices)
    message = models.TextField(help_text="Human-readable event description")
    execution_results = models.JSONField(
        validators=[validate_execution_results],
        default=list,
        blank=True,
    )
    telemetry_snapshot = models.JSONField(
        validators=[validate_telemetry_snapshot],
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20, choices=EventStatus.choices, default=EventStatus.NEW
    )

    class Meta:
        db_table = "events"
        ordering = ["-timestamp", "-id"]
        indexes = [
            models.Index(fields=["rule_id"], name="idx_event_rule_id"),
            models.Index(fields=["device_id"], name="idx_event_device_id"),
            models.Index(fields=["status", "timestamp"], name="idx_event_status_time"),
            models.Index(fields=["severity", "timestamp"], name="idx_event_severity_time"),
        ]

    def __str__(self):
        return f"Event {self.id} - Rule {self.rule_id} - {self.severity}"

    @property
    def acknowledged(self) -> bool:
        return self.status != Event.EventStatus.NEW
