from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from app.services.event_service import (
    ApiError,
    acknowledge_event,
    build_event_export,
    create_event,
    get_event_or_404,
    paginated_events,
    parse_json_body,
    resolve_event,
    serialize_event,
    update_event,
)


logger = logging.getLogger(__name__)


def handle_api_error(exc: ApiError) -> JsonResponse:
    return JsonResponse({"detail": exc.detail}, status=exc.status_code)


@method_decorator(csrf_exempt, name="dispatch")
class EventListView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        try:
            payload = paginated_events(request=request)
        except ApiError as exc:
            return handle_api_error(exc)
        return JsonResponse(payload, status=200)

    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            event = create_event(parse_json_body(request))
        except ApiError as exc:
            return handle_api_error(exc)
        return JsonResponse({"data": serialize_event(event)}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class EventDetailView(View):
    def get(self, request: HttpRequest, event_id: int) -> JsonResponse:  # noqa: ARG002
        try:
            event = get_event_or_404(event_id)
        except ApiError as exc:
            return handle_api_error(exc)
        return JsonResponse({"data": serialize_event(event)}, status=200)

    def put(self, request: HttpRequest, event_id: int) -> JsonResponse:
        return self._update(request, event_id, partial=False)

    def patch(self, request: HttpRequest, event_id: int) -> JsonResponse:
        return self._update(request, event_id, partial=True)

    def delete(self, request: HttpRequest, event_id: int) -> HttpResponse:  # noqa: ARG002
        try:
            event = get_event_or_404(event_id)
        except ApiError as exc:
            return handle_api_error(exc)
        event.delete()
        return HttpResponse(status=204)

    def _update(
        self, request: HttpRequest, event_id: int, partial: bool
    ) -> JsonResponse:
        try:
            event = get_event_or_404(event_id)
            updated = update_event(event, parse_json_body(request), partial=partial)
        except ApiError as exc:
            return handle_api_error(exc)
        return JsonResponse({"data": serialize_event(updated)}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class EventAcknowledgeView(View):
    def post(self, request: HttpRequest, event_id: int) -> JsonResponse:  # noqa: ARG002
        try:
            event = get_event_or_404(event_id)
            updated = acknowledge_event(event)
        except ApiError as exc:
            return handle_api_error(exc)

        logger.info(
            "event.acknowledged",
            extra={
                "event_id": updated.id,
                "rule_id": str(updated.rule_id),
                "device_id": str(updated.device_id),
                "status": updated.status,
            },
        )
        return JsonResponse({"data": serialize_event(updated)}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class EventResolveView(View):
    def post(self, request: HttpRequest, event_id: int) -> JsonResponse:  # noqa: ARG002
        try:
            event = get_event_or_404(event_id)
            updated = resolve_event(event)
        except ApiError as exc:
            return handle_api_error(exc)

        logger.info(
            "event.resolved",
            extra={
                "event_id": updated.id,
                "rule_id": str(updated.rule_id),
                "device_id": str(updated.device_id),
                "status": updated.status,
            },
        )
        return JsonResponse({"data": serialize_event(updated)}, status=200)


class EventExportView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        try:
            csv_payload = build_event_export(request=request)
        except ApiError as exc:
            return handle_api_error(exc)

        response = HttpResponse(csv_payload, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="events_export.csv"'
        return response
