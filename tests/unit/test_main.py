from unittest.mock import Mock

from app.main import main


def test_main_runs_server_only(monkeypatch):
    execute = Mock()
    monkeypatch.setattr("app.main.execute_from_command_line", execute)
    monkeypatch.setattr("app.main.load_env_file", Mock())
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "8012")

    main()

    execute.assert_called_once_with(
        ["manage.py", "runserver", "127.0.0.1:8012", "--noreload"]
    )
