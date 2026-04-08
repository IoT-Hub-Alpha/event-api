from django.urls import path

from app.api.views import (
    EventAcknowledgeView,
    EventDetailView,
    EventExportView,
    EventListView,
    EventResolveView,
)


urlpatterns = [
    path("events/", EventListView.as_view(), name="event-list"),
    path("events/export/", EventExportView.as_view(), name="event-export"),
    path("events/<int:event_id>/", EventDetailView.as_view(), name="event-detail"),
    path("events/<int:event_id>/ack/", EventAcknowledgeView.as_view(), name="event-ack"),
    path(
        "events/<int:event_id>/resolve/",
        EventResolveView.as_view(),
        name="event-resolve",
    ),
]
