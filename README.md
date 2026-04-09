# event-api

Standalone Django microservice for event management and export.

## Endpoints

- `GET /health/`
- `GET /ready/`
- `GET /v1/events/`
- `POST /v1/events/`
- `GET /v1/events/{id}/`
- `PUT /v1/events/{id}/`
- `PATCH /v1/events/{id}/`
- `DELETE /v1/events/{id}/`
- `POST /v1/events/{id}/ack/`
- `POST /v1/events/{id}/resolve/`
- `GET /v1/events/export/`

## Local Run

```bash
cp .env.example .env
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python manage.py ensure_db_schema
python manage.py migrate
python manage.py seed_events --count 20
python -m app.main
```

Use Python 3.13 for local development. The service Docker image already runs on
`python:3.13-slim`, and the shared `logging-lib` dependency currently requires
Python 3.13.

## CSV Export

`GET /v1/events/export/` applies the same filters as the list endpoint.

Optional query params:
- `full=true` to include JSON payload columns

Structured logging is enabled through the shared `logging-lib` package.
All HTTP responses include `X-Request-ID`, and application logs are emitted as
JSON with request context when available.

JWT auth is enabled through the shared `jwt-auth-lib` package. Protected API
endpoints accept bearer tokens or the configured internal service header.

When using the authentication microservice, the issued access token must
include these permission strings for `event-api`:
- `events.view_event` for list/detail/export
- `events.change_event` for create/update/delete/ack/resolve

## Testing

```bash
pytest
```
