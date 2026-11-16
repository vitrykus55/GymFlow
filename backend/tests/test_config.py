from app.core.config import Settings


def test_migrations_prefer_the_direct_database_url() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://pooled",
        database_url_unpooled="postgresql+psycopg://direct",
    )

    assert settings.migration_database_url == "postgresql+psycopg://direct"


def test_migrations_fall_back_to_the_application_database_url() -> None:
    settings = Settings(database_url="postgresql+psycopg://local")

    assert settings.migration_database_url == "postgresql+psycopg://local"


def test_plain_postgres_urls_use_the_psycopg_driver() -> None:
    settings = Settings(
        database_url="postgresql://user:pw@host/db?sslmode=require",
        database_url_unpooled="postgres://user:pw@host/db",
    )

    assert settings.database_url == "postgresql+psycopg://user:pw@host/db?sslmode=require"
    assert settings.database_url_unpooled == "postgresql+psycopg://user:pw@host/db"
