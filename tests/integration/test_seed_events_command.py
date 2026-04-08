from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from app.api.models import Event


@pytest.mark.django_db
def test_seed_events_command_creates_sample_events():
    stdout = StringIO()
    result = call_command("seed_events", count=3, stdout=stdout)

    assert result is None
    assert Event.objects.count() == 3
    assert "Seeded 3 events." in stdout.getvalue()

    seeded = list(Event.objects.order_by("id"))
    assert seeded[0].message.startswith("Seed event 1:")
    assert seeded[0].telemetry_snapshot["device_id"] == str(seeded[0].device_id)
    assert seeded[1].status in Event.EventStatus.values
    assert seeded[2].severity in Event.EventSeverity.values


@pytest.mark.django_db
def test_seed_events_command_rejects_non_positive_count():
    with pytest.raises(CommandError, match="--count must be >= 1."):
        call_command("seed_events", count=0)
