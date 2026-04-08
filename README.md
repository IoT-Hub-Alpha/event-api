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
pip install -r requirements.txt -r requirements-dev.txt
python manage.py ensure_db_schema
python manage.py migrate
python manage.py seed_events --count 20
python -m app.main
```

## CSV Export

`GET /v1/events/export/` applies the same filters as the list endpoint.

Optional query params:
- `full=true` to include JSON payload columns

Auth and structured logging are intentionally deferred for the first pass.

## Testing

```bash
pytest
```
