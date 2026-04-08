from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.paginator import EmptyPage, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest

from app.api.models import Event


class ApiError(Exception):
    def __init__(self, detail: Any, status_code: int = 400):
        super().__init__(str(detail))
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class EventFilters:
    device_id: UUID | None = None
    rule_id: UUID | None = None
    severity: str | None = None
    acknowledged: bool | None = None


def parse_json_body(request: HttpRequest) -> dict[str, Any]:
    if not request.body:
        return {}

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiError("Request body must be valid JSON.", status_code=400) from exc

    if not isinstance(payload, dict):
        raise ApiError("Request body must be a JSON object.", status_code=400)

    return payload


def serialize_event(event: Event) -> dict[str, Any]:
    snapshot = event.telemetry_snapshot or {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    created_at = event.timestamp.isoformat()
    fired_at = snapshot.get("timestamp")
    if not isinstance(fired_at, str) or not fired_at:
        fired_at = created_at

    return {
        "id": event.id,
        "rule_id": str(event.rule_id),
        "device_id": str(event.device_id),
        "severity": event.severity,
        "message": event.message,
        "status": event.status,
        "acknowledged": event.acknowledged,
        "fired_at": fired_at,
        "created_at": created_at,
        "execution_results": event.execution_results,
        "telemetry_snapshot": event.telemetry_snapshot,
        "payload": snapshot.get("payload"),
    }


def parse_bool(raw: str, *, field_name: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ApiError(f"{field_name} must be true/false.", status_code=400)


def parse_positive_int(
    raw: str | None,
    *,
    field_name: str,
    default: int,
    max_value: int | None = None,
) -> int:
    if raw is None:
        return default

    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ApiError(f"{field_name} must be an integer.", status_code=400) from exc

    if value < 1:
        raise ApiError(f"{field_name} must be >= 1.", status_code=400)

    if max_value is not None and value > max_value:
        raise ApiError(f"{field_name} must be <= {max_value}.", status_code=400)

    return value


def parse_uuid(raw: str | None, *, field_name: str, required: bool) -> UUID | None:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if required:
            raise ApiError({field_name: "This field is required."}, status_code=400)
        return None

    try:
        return UUID(str(raw))
    except (TypeError, ValueError) as exc:
        raise ApiError({field_name: "Must be a valid UUID."}, status_code=400) from exc


def parse_filters(request: HttpRequest) -> EventFilters:
    device_raw = request.GET.get("device") or request.GET.get("device_id")
    rule_raw = request.GET.get("rule") or request.GET.get("rule_id")
    severity = request.GET.get("severity")

    if severity is not None:
        allowed = {choice for choice, _ in Event.EventSeverity.choices}
        if severity not in allowed:
            raise ApiError("Invalid severity filter value.", status_code=400)

    acknowledged_raw = request.GET.get("acknowledged")
    acknowledged = (
        parse_bool(acknowledged_raw, field_name="acknowledged")
        if acknowledged_raw is not None
        else None
    )

    return EventFilters(
        device_id=parse_uuid(device_raw, field_name="device_id", required=False),
        rule_id=parse_uuid(rule_raw, field_name="rule_id", required=False),
        severity=severity,
        acknowledged=acknowledged,
    )


def apply_filters(queryset: QuerySet[Event], filters: EventFilters) -> QuerySet[Event]:
    if filters.device_id is not None:
        queryset = queryset.filter(device_id=filters.device_id)
    if filters.rule_id is not None:
        queryset = queryset.filter(rule_id=filters.rule_id)
    if filters.severity:
        queryset = queryset.filter(severity=filters.severity)
    if filters.acknowledged is True:
        queryset = queryset.exclude(status=Event.EventStatus.NEW)
    elif filters.acknowledged is False:
        queryset = queryset.filter(status=Event.EventStatus.NEW)
    return queryset


def paginated_events(*, request: HttpRequest) -> dict[str, Any]:
    filters = parse_filters(request)
    page = parse_positive_int(
        request.GET.get("page"),
        field_name="page",
        default=1,
    )
    page_size = parse_positive_int(
        request.GET.get("page_size"),
        field_name="page_size",
        default=20,
        max_value=1000,
    )

    queryset = apply_filters(Event.objects.all(), filters)
    paginator = Paginator(queryset, page_size)

    if paginator.count == 0:
        return {
            "data": [],
            "pagination": {
                "page": 1,
                "page_size": page_size,
                "total": 0,
                "total_pages": 0,
                "next_page": None,
                "prev_page": None,
            },
        }

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return {
        "data": [serialize_event(item) for item in page_obj.object_list],
        "pagination": {
            "page": page_obj.number,
            "page_size": page_size,
            "total": paginator.count,
            "total_pages": paginator.num_pages,
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "prev_page": (
                page_obj.previous_page_number() if page_obj.has_previous() else None
            ),
        },
    }


def get_event_or_404(event_id: int) -> Event:
    event = Event.objects.filter(id=event_id).first()
    if event is None:
        raise ApiError("Event not found.", status_code=404)
    return event


def _normalize_payload(
    data: dict[str, Any],
    *,
    partial: bool,
    creating: bool,
) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}

    if creating or "rule_id" in data:
        cleaned["rule_id"] = parse_uuid(
            data.get("rule_id"), field_name="rule_id", required=creating
        )
    if creating or "device_id" in data:
        cleaned["device_id"] = parse_uuid(
            data.get("device_id"), field_name="device_id", required=creating
        )

    for field_name in ("rule_name", "device_serial", "message"):
        if field_name in data:
            value = data.get(field_name)
            if value is None:
                normalized = ""
            elif not isinstance(value, str):
                raise ApiError({field_name: "Must be a string."}, status_code=400)
            else:
                normalized = value.strip()

            if field_name == "message" and not normalized:
                raise ApiError(
                    {field_name: "This field may not be blank."},
                    status_code=400,
                )
            cleaned[field_name] = normalized
        elif creating and field_name == "message" and not partial:
            raise ApiError({field_name: "This field is required."}, status_code=400)

    if "severity" in data or creating:
        severity = data.get("severity")
        if severity is None and creating:
            raise ApiError({"severity": "This field is required."}, status_code=400)
        if severity is not None:
            allowed = {choice for choice, _ in Event.EventSeverity.choices}
            if severity not in allowed:
                raise ApiError(
                    {"severity": f"Invalid severity. Allowed: {', '.join(sorted(allowed))}"},
                    status_code=400,
                )
            cleaned["severity"] = severity

    if "status" in data:
        status = data.get("status")
        allowed = {choice for choice, _ in Event.EventStatus.choices}
        if status not in allowed:
            raise ApiError(
                {"status": f"Invalid status. Allowed: {', '.join(sorted(allowed))}"},
                status_code=400,
            )
        cleaned["status"] = status
    elif creating:
        cleaned["status"] = Event.EventStatus.NEW

    if "execution_results" in data:
        execution_results = data["execution_results"]
        if not isinstance(execution_results, list):
            raise ApiError({"execution_results": "Must be a list."}, status_code=400)
        cleaned["execution_results"] = execution_results
    elif creating:
        cleaned["execution_results"] = []

    if "telemetry_snapshot" in data:
        telemetry_snapshot = data["telemetry_snapshot"]
        if telemetry_snapshot is not None and not isinstance(telemetry_snapshot, dict):
            raise ApiError(
                {"telemetry_snapshot": "Must be an object or null."},
                status_code=400,
            )
        cleaned["telemetry_snapshot"] = telemetry_snapshot
    elif creating:
        cleaned["telemetry_snapshot"] = None

    if creating:
        cleaned.setdefault("rule_name", "")
        cleaned.setdefault("device_serial", "")

    return cleaned


def _save_event(event: Event) -> Event:
    try:
        event.full_clean()
    except DjangoValidationError as exc:
        raise ApiError(exc.message_dict, status_code=400) from exc

    event.save()
    return event


def create_event(data: dict[str, Any]) -> Event:
    event = Event(**_normalize_payload(data, partial=False, creating=True))
    return _save_event(event)


def update_event(event: Event, data: dict[str, Any], *, partial: bool) -> Event:
    cleaned = _normalize_payload(data, partial=partial, creating=False)
    for key, value in cleaned.items():
        setattr(event, key, value)
    return _save_event(event)


def acknowledge_event(event: Event) -> Event:
    if event.status == Event.EventStatus.NEW:
        event.status = Event.EventStatus.ACKNOWLEDGED
        event.save(update_fields=["status"])
    return event


def resolve_event(event: Event) -> Event:
    if event.status != Event.EventStatus.RESOLVED:
        event.status = Event.EventStatus.RESOLVED
        event.save(update_fields=["status"])
    return event


def build_event_export(*, request: HttpRequest) -> str:
    filters = parse_filters(request)
    full = (
        parse_bool(request.GET.get("full"), field_name="full")
        if request.GET.get("full") is not None
        else False
    )

    queryset = apply_filters(Event.objects.order_by("timestamp", "id"), filters)
    fieldnames = [
        "id",
        "fired_at",
        "rule_name",
        "rule_id",
        "device_serial",
        "device_id",
        "severity",
        "status",
        "acknowledged",
        "message",
    ]
    if full:
        fieldnames.extend(["execution_results", "telemetry_snapshot", "payload"])

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()

    for event in queryset.iterator():
        serialized = serialize_event(event)
        row = {
            "id": event.id,
            "fired_at": serialized["fired_at"],
            "rule_name": event.rule_name,
            "rule_id": serialized["rule_id"],
            "device_serial": event.device_serial,
            "device_id": serialized["device_id"],
            "severity": event.severity,
            "status": event.status,
            "acknowledged": event.acknowledged,
            "message": event.message,
        }
        if full:
            row.update(
                {
                    "execution_results": json.dumps(event.execution_results),
                    "telemetry_snapshot": json.dumps(event.telemetry_snapshot),
                    "payload": json.dumps(serialized["payload"])
                    if serialized["payload"] is not None
                    else "",
                }
            )
        writer.writerow(row)

    return buffer.getvalue()
