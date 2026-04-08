#!/usr/bin/env python
import os
import sys

from config.env import load_env_file


def main() -> None:
    load_env_file()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
