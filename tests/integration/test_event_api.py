import json
from uuid import uuid4

import pytest

from app.api.models import Event


@pytest.mark.django_db
def test_create_event(client):
    response = client.post(
        "/v1/events/",
        data=json.dumps(
            {
                "rule_id": str(uuid4()),
                "device_id": str(uuid4()),
                "severity": "warning",
                "message": "High temperature detected",
                "rule_name": "High Temp",
                "device_serial": "TEMP-001",
                "telemetry_snapshot": {
                    "device_id": str(uuid4()),
                    "timestamp": "2026-02-08T18:22:00Z",
                    "payload": {"value": 84.3},
                },
                "execution_results": [
                    {"type": "notification", "template_id": 5, "status": "completed"}
                ],
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()["data"]
    assert payload["status"] == "new"
    assert payload["acknowledged"] is False
    assert payload["payload"] == {"value": 84.3}


@pytest.mark.django_db
def test_list_events_filters_and_paginates(client):
    device_id = uuid4()
    other_device_id = uuid4()

    Event.objects.create(
        rule_id=uuid4(),
        device_id=device_id,
        severity=Event.EventSeverity.WARNING,
        message="event-1",
        telemetry_snapshot={
            "device_id": str(device_id),
            "timestamp": "2026-01-15T10:30:00+00:00",
            "payload": {"values": [11.0]},
        },
        status=Event.EventStatus.NEW,
    )
    Event.objects.create(
        rule_id=uuid4(),
        device_id=other_device_id,
        severity=Event.EventSeverity.INFO,
        message="event-2",
        telemetry_snapshot={
            "device_id": str(other_device_id),
            "timestamp": "2026-01-16T10:30:00+00:00",
            "payload": {"values": [12.0]},
        },
        status=Event.EventStatus.ACKNOWLEDGED,
    )

    response = client.get(f"/v1/events/?device_id={device_id}&page=1&page_size=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["data"][0]["message"] == "event-1"
    assert payload["data"][0]["acknowledged"] is False


@pytest.mark.django_db
def test_ack_event_updates_status(client):
    event = Event.objects.create(
        rule_id=uuid4(),
        device_id=uuid4(),
        severity=Event.EventSeverity.WARNING,
        message="event-1",
        telemetry_snapshot={"payload": {"values": [11.0]}},
        status=Event.EventStatus.NEW,
    )

    response = client.post(f"/v1/events/{event.id}/ack/")

    assert response.status_code == 200
    event.refresh_from_db()
    assert event.status == Event.EventStatus.ACKNOWLEDGED
    assert response.json()["data"]["status"] == Event.EventStatus.ACKNOWLEDGED


@pytest.mark.django_db
def test_resolve_event_updates_status(client):
    event = Event.objects.create(
        rule_id=uuid4(),
        device_id=uuid4(),
        severity=Event.EventSeverity.WARNING,
        message="event-1",
        telemetry_snapshot={"payload": {"values": [11.0]}},
        status=Event.EventStatus.ACKNOWLEDGED,
    )

    response = client.post(f"/v1/events/{event.id}/resolve/")

    assert response.status_code == 200
    event.refresh_from_db()
    assert event.status == Event.EventStatus.RESOLVED
    assert response.json()["data"]["status"] == Event.EventStatus.RESOLVED


@pytest.mark.django_db
def test_export_events_returns_csv(client):
    event = Event.objects.create(
        rule_id=uuid4(),
        device_id=uuid4(),
        rule_name="High Temp",
        device_serial="TEMP-001",
        severity=Event.EventSeverity.WARNING,
        message="event-1",
        telemetry_snapshot={
            "timestamp": "2026-01-15T10:30:00+00:00",
            "payload": {"values": [11.0]},
        },
        status=Event.EventStatus.NEW,
    )

    response = client.get(f"/v1/events/export/?rule_id={event.rule_id}")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "events_export.csv" in response["Content-Disposition"]
    body = response.content.decode("utf-8")
    assert "rule_name,rule_id,device_serial,device_id" in body
    assert "High Temp" in body


@pytest.mark.django_db
def test_delete_event(client):
    event = Event.objects.create(
        rule_id=uuid4(),
        device_id=uuid4(),
        severity=Event.EventSeverity.INFO,
        message="event-1",
        telemetry_snapshot={"payload": {"values": [11.0]}},
    )

    response = client.delete(f"/v1/events/{event.id}/")

    assert response.status_code == 204
    assert Event.objects.filter(id=event.id).exists() is False
