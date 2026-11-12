from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.security import verify_password
from app.db.session import get_db
from app.main import app
from app.models.user import User


class DuplicateEmailViolation(Exception):
    sqlstate = "23505"

    class diag:
        constraint_name = "ux_users_email_lower"


class InMemoryRegistrationSession:
    def __init__(self) -> None:
        self.users: list[User] = []
        self.pending_user: User | None = None
        self.duplicate_on_commit = False
        self.rollback_calls = 0

    def scalar(self, statement: Any) -> int | None:
        email = next(iter(statement.compile().params.values()))
        return next((user.id for user in self.users if user.email.lower() == email), None)

    def add(self, user: User) -> None:
        self.pending_user = user

    def commit(self) -> None:
        if self.duplicate_on_commit:
            raise IntegrityError("INSERT INTO users", {}, DuplicateEmailViolation())

        assert self.pending_user is not None
        self.pending_user.id = len(self.users) + 1
        self.users.append(self.pending_user)

    def rollback(self) -> None:
        self.rollback_calls += 1

    def refresh(self, user: User) -> None:
        assert user in self.users


@pytest.fixture
def registration_session() -> InMemoryRegistrationSession:
    return InMemoryRegistrationSession()


@pytest.fixture
def client(registration_session: InMemoryRegistrationSession) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[InMemoryRegistrationSession]:
        yield registration_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def registration_payload() -> dict[str, str]:
    return {
        "email": "User@Example.COM ",
        "password": "correct horse battery staple",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "phone": "+48123123123",
        "birth_date": "1815-12-10",
    }


def test_register_user_creates_client_with_hashed_password(
    client: TestClient,
    registration_session: InMemoryRegistrationSession,
    registration_payload: dict[str, str],
) -> None:
    response = client.post("/api/v1/auth/register", json=registration_payload)

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "email": "user@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "role": "client",
    }
    stored_user = registration_session.users[0]
    assert stored_user.password_hash != registration_payload["password"]
    assert verify_password(registration_payload["password"], stored_user.password_hash) is True
    assert str(stored_user.role) == "client"
    assert "password_hash" not in response.json()


def test_register_user_rejects_duplicate_email(
    client: TestClient, registration_payload: dict[str, str]
) -> None:
    assert client.post("/api/v1/auth/register", json=registration_payload).status_code == 201

    duplicate_payload = {**registration_payload, "email": "USER@example.com"}
    response = client.post("/api/v1/auth/register", json=duplicate_payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered."}


def test_register_user_handles_concurrent_duplicate_email(
    client: TestClient,
    registration_session: InMemoryRegistrationSession,
    registration_payload: dict[str, str],
) -> None:
    registration_session.duplicate_on_commit = True

    response = client.post("/api/v1/auth/register", json=registration_payload)

    assert response.status_code == 409
    assert registration_session.rollback_calls == 1


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("role", "admin"), ("is_active", False), ("password_hash", "not-a-hash")],
)
def test_register_user_rejects_privileged_and_internal_fields(
    client: TestClient,
    registration_payload: dict[str, str],
    field_name: str,
    value: str | bool,
) -> None:
    response = client.post(
        "/api/v1/auth/register", json={**registration_payload, field_name: value}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"email": "not-an-email", "password": "correct horse battery staple"},
        {
            "email": "user@example.com",
            "password": "short",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    ],
)
def test_register_user_rejects_invalid_input(
    client: TestClient, invalid_payload: dict[str, str]
) -> None:
    response = client.post("/api/v1/auth/register", json=invalid_payload)

    assert response.status_code == 422
