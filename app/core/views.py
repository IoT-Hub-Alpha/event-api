from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor
from django.http import JsonResponse


def health(request):  # noqa: ARG001
    return JsonResponse({"status": "ok"})


def has_pending_migrations() -> bool:
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    return bool(executor.migration_plan(targets))


def ready(request):  # noqa: ARG001
    try:
        connection.ensure_connection()
        if has_pending_migrations():
            return JsonResponse(
                {"status": "not_ready", "detail": "Pending migrations."},
                status=503,
            )
    except DatabaseError:
        return JsonResponse({"status": "not_ready"}, status=503)
    return JsonResponse({"status": "ready"})
