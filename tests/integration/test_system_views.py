from unittest.mock import Mock

import pytest
from django.db import DatabaseError


@pytest.mark.django_db
def test_health_endpoint_returns_ok_and_request_id_header(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response
    assert response["X-Request-ID"]


@pytest.mark.django_db
def test_health_endpoint_reuses_incoming_request_id(client):
    response = client.get("/health/", HTTP_X_REQUEST_ID="test-request-id")

    assert response.status_code == 200
    assert response["X-Request-ID"] == "test-request-id"


@pytest.mark.django_db
def test_ready_endpoint_returns_ready(client, monkeypatch):
    ensure_connection = Mock()
    monkeypatch.setattr(
        "app.core.views.connection.ensure_connection",
        ensure_connection,
    )
    monkeypatch.setattr(
        "app.core.views.has_pending_migrations", Mock(return_value=False)
    )

    response = client.get("/ready/")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    ensure_connection.assert_called_once_with()


@pytest.mark.django_db
def test_ready_endpoint_returns_not_ready_on_database_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.views.connection.ensure_connection",
        Mock(side_effect=DatabaseError),
    )

    response = client.get("/ready/")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


@pytest.mark.django_db
def test_ready_endpoint_returns_not_ready_when_migrations_are_pending(
    client, monkeypatch
):
    monkeypatch.setattr("app.core.views.connection.ensure_connection", Mock())
    monkeypatch.setattr(
        "app.core.views.has_pending_migrations", Mock(return_value=True)
    )

    response = client.get("/ready/")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "detail": "Pending migrations.",
    }
