from app.api.management.commands.ensure_db_schema import should_ensure_schema


def test_should_ensure_schema_only_for_non_public_postgres():
    assert should_ensure_schema("postgresql", "events") is True
    assert should_ensure_schema("postgresql", "public") is False
    assert should_ensure_schema("sqlite", "events") is False
