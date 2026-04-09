import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from django.test import override_settings


def make_access_token(*, permissions: list[str]) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": "1",
        "username": "operator",
        "email": "operator@example.com",
        "groups": ["Operators"],
        "permissions": permissions,
        "is_staff": True,
        "is_superuser": False,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, "test-jwt-secret", algorithm="HS256")


@pytest.mark.django_db
def test_public_health_endpoint_bypasses_auth(raw_client):
    response = raw_client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_protected_endpoint_rejects_missing_token(raw_client):
    response = raw_client.get("/v1/events/")

    assert response.status_code == 400
    assert response.json() == {"error": "invalid token"}


@pytest.mark.django_db
def test_internal_service_header_bypasses_auth(client):
    response = client.get("/v1/events/")

    assert response.status_code == 200
    assert "data" in response.json()


@pytest.mark.django_db
@override_settings(JWT_SECRET_KEY="test-jwt-secret")
def test_valid_token_with_required_permission_is_allowed(raw_client):
    token = make_access_token(permissions=["events.view_event"])

    response = raw_client.get(
        "/v1/events/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert "data" in response.json()


@pytest.mark.django_db
@override_settings(JWT_SECRET_KEY="test-jwt-secret")
def test_valid_token_with_change_permission_can_create_event(raw_client):
    token = make_access_token(permissions=["events.change_event"])

    response = raw_client.post(
        "/v1/events/",
        data=json.dumps(
            {
                "rule_id": "11111111-1111-1111-1111-111111111111",
                "device_id": "22222222-2222-2222-2222-222222222222",
                "severity": "warning",
                "message": "High temperature detected",
            }
        ),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201
    assert response.json()["data"]["status"] == "new"


@pytest.mark.django_db
@override_settings(JWT_SECRET_KEY="test-jwt-secret")
def test_valid_token_without_change_permission_cannot_create_event(raw_client):
    token = make_access_token(permissions=["events.view_event"])

    response = raw_client.post(
        "/v1/events/",
        data=json.dumps(
            {
                "rule_id": "11111111-1111-1111-1111-111111111111",
                "device_id": "22222222-2222-2222-2222-222222222222",
                "severity": "warning",
                "message": "High temperature detected",
            }
        ),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 401
    assert response.json() == {"error": "Not authorized"}


@pytest.mark.django_db
@override_settings(JWT_SECRET_KEY="test-jwt-secret")
def test_valid_token_without_required_permission_is_rejected(raw_client):
    token = make_access_token(permissions=["users.view"])

    response = raw_client.get(
        "/v1/events/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 401
    assert response.json() == {"error": "Not authorized"}
