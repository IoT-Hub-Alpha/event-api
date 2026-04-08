from django.db import migrations, models

import app.api.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("rule_id", models.UUIDField()),
                ("device_id", models.UUIDField()),
                ("rule_name", models.CharField(blank=True, default="", max_length=255)),
                (
                    "device_serial",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("critical", "Critical"),
                            ("warning", "Warning"),
                            ("info", "Info"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "message",
                    models.TextField(help_text="Human-readable event description"),
                ),
                (
                    "execution_results",
                    models.JSONField(
                        blank=True,
                        default=list,
                        validators=[app.api.models.validate_execution_results],
                    ),
                ),
                (
                    "telemetry_snapshot",
                    models.JSONField(
                        blank=True,
                        null=True,
                        validators=[app.api.models.validate_telemetry_snapshot],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("acknowledged", "Acknowledged"),
                            ("resolved", "Resolved"),
                        ],
                        default="new",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "db_table": "events",
                "ordering": ["-timestamp", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["rule_id"], name="idx_event_rule_id"),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["device_id"], name="idx_event_device_id"),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["status", "timestamp"], name="idx_event_status_time"
            ),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["severity", "timestamp"], name="idx_event_severity_time"
            ),
        ),
    ]
