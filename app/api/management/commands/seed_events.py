from __future__ import annotations

from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from app.api.models import Event

DEFAULT_SEED_COUNT = 20
SEED_POOL_SIZE = 6


def build_seed_event(index: int, *, base_time: datetime) -> tuple[dict, datetime]:
    slot = index % SEED_POOL_SIZE
    sequence = index + 1
    severity = list(Event.EventSeverity.values)[index % len(Event.EventSeverity.values)]
    status = list(Event.EventStatus.values)[index % len(Event.EventStatus.values)]

    rule_id = uuid5(NAMESPACE_URL, f"event-api/seed/rule/{slot}")
    device_id = uuid5(NAMESPACE_URL, f"event-api/seed/device/{slot}")
    fired_at = base_time - timedelta(hours=index * 2, minutes=slot * 5)
    temperature = round(22.5 + (slot * 3.2) + (index * 0.6), 1)

    execution_results = []
    if status != Event.EventStatus.NEW:
        execution_results.append(
            {
                "type": "notification",
                "status": "completed",
                "template_id": slot + 1,
            }
        )

    payload = {
        "rule_id": rule_id,
        "device_id": device_id,
        "rule_name": f"Seed Rule {slot + 1}",
        "device_serial": f"SEED-{slot + 1:03d}",
        "severity": severity,
        "message": (
            f"Seed event {sequence}: {severity} threshold reached "
            f"on device {slot + 1}"
        ),
        "status": status,
        "execution_results": execution_results,
        "telemetry_snapshot": {
            "device_id": str(device_id),
            "timestamp": fired_at.isoformat(),
            "payload": {
                "metric": "temperature_c",
                "value": temperature,
                "unit": "C",
            },
        },
    }
    return payload, fired_at


def seed_events(count: int, *, base_time=None) -> int:
    seeded = 0
    current_time = base_time or timezone.now()

    with transaction.atomic():
        for index in range(count):
            event_data, fired_at = build_seed_event(index, base_time=current_time)
            event = Event.objects.create(**event_data)
            event.timestamp = fired_at
            event.save(update_fields=["timestamp"])
            seeded += 1

    return seeded


class Command(BaseCommand):
    help = "Seed sample events for local manual testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=DEFAULT_SEED_COUNT,
            help=f"Number of events to create (default: {DEFAULT_SEED_COUNT})",
        )

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be >= 1.")

        created = seed_events(count)
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} events."))
