import os

from django.core.management import execute_from_command_line

from config.env import load_env_file


def main() -> None:
    load_env_file()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from app.core.config import settings

    execute_from_command_line(
        ["manage.py", "runserver", f"{settings.host}:{settings.port}", "--noreload"]
    )


if __name__ == "__main__":
    main()
