"""Optional PostgreSQL integration checks.

PowerShell:
    $env:TEST_DATABASE_URL = "<dedicated PostgreSQL test database URL>"
    docker compose exec -e TEST_DATABASE_URL backend pytest -m integration
"""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import verify_password
from app.db.session import get_db
from app.main import app
from app.models.user import User


def _is_same_database(test_database_url: str) -> bool:
    test_url = make_url(test_database_url)
    app_url = make_url(settings.database_url)
    return (
        (test_url.host or "").replace("-pooler", "") == (app_url.host or "").replace("-pooler", "")
        and (test_url.port or 5432) == (app_url.port or 5432)
        and test_url.database == app_url.database
    )


@pytest.mark.integration
def test_postgresql_test_database_executes_select_one() -> None:
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL test database.")

    test_url = make_url(test_database_url)
    if test_url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL.")

    if _is_same_database(test_database_url):
        pytest.skip("TEST_DATABASE_URL matches DATABASE_URL; refusing shared-database access.")

    engine = create_engine(test_url, poolclass=NullPool, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()


@pytest.mark.integration
def test_registration_persists_client_to_test_postgresql() -> None:
    """Exercise the registration API against a dedicated, already-migrated database."""
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL test database.")

    test_url = make_url(test_database_url)
    if test_url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL.")
    if _is_same_database(test_database_url):
        pytest.skip("TEST_DATABASE_URL matches DATABASE_URL; refusing shared-database writes.")

    engine = create_engine(test_url, poolclass=NullPool, pool_pre_ping=True)
    test_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    email = f"gymflow-integration-{uuid4().hex}@example.com"
    password = "integration-test-password"
    previous_override = app.dependency_overrides.get(get_db)

    def override_get_db():
        with test_sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "first_name": "Integration",
                    "last_name": "Client",
                },
            )

        assert response.status_code == 201
        assert response.json()["email"] == email
        with Session(engine) as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            assert user.role.value == "client"
            assert user.password_hash != password
            assert verify_password(password, user.password_hash)
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override

        with Session(engine) as db:
            user = db.scalar(select(User).where(User.email == email))
            if user is not None:
                db.delete(user)
                db.commit()
        engine.dispose()
