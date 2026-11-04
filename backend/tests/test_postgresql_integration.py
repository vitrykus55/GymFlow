"""Optional read-only PostgreSQL integration check.

PowerShell:
    $env:TEST_DATABASE_URL = "<dedicated PostgreSQL test database URL>"
    docker compose exec -e TEST_DATABASE_URL backend pytest -m integration
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.core.config import settings


@pytest.mark.integration
def test_postgresql_test_database_executes_select_one() -> None:
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL test database.")

    test_url = make_url(test_database_url)
    if test_url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL.")

    app_url = make_url(settings.database_url)
    same_database = (
        (test_url.host or "").replace("-pooler", "") == (app_url.host or "").replace("-pooler", "")
        and (test_url.port or 5432) == (app_url.port or 5432)
        and test_url.database == app_url.database
    )
    if same_database:
        pytest.skip("TEST_DATABASE_URL matches DATABASE_URL; refusing shared-database access.")

    engine = create_engine(test_url, poolclass=NullPool, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()
