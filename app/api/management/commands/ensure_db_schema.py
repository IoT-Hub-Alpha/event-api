import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.utils import ProgrammingError


def should_ensure_schema(connection_vendor: str, schema_name: str) -> bool:
    return connection_vendor == "postgresql" and schema_name != "public"


class Command(BaseCommand):
    help = "Create the configured PostgreSQL schema when the service owns it."

    def handle(self, *args, **options):
        schema_name = os.getenv("DB_SCHEMA", "public").strip() or "public"

        if not should_ensure_schema(connection.vendor, schema_name):
            self.stdout.write("Schema bootstrap skipped.")
            return

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name],
            )
            if cursor.fetchone():
                self.stdout.write(f'Schema "{schema_name}" already exists.')
                return

        quoted_schema = connection.ops.quote_name(schema_name)
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE SCHEMA {quoted_schema}")
        except ProgrammingError as exc:
            database_name = connection.settings_dict["NAME"]
            database_user = connection.settings_dict["USER"]
            raise CommandError(
                "Unable to create schema "
                f'"{schema_name}". Grant CREATE on database '
                f'"{database_name}" to "{database_user}", '
                "or create the schema as an admin user first."
            ) from exc

        self.stdout.write(self.style.SUCCESS(f'Schema "{schema_name}" ensured.'))
