from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

from app.core import security
from app.db.session import get_db
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

TEST_JWT_SECRET = "test-jwt-secret-key-that-is-at-least-32-characters-long"


class DuplicateEmailViolation(Exception):
    sqlstate = "23505"

    class diag:
        constraint_name = "ux_users_email_lower"


class InMemoryUserSession:
    def __init__(self) -> None:
        self.users: list[User] = []
        self.duplicate_on_commit = False
        self.rollback_calls = 0

    def scalar(self, statement: Any) -> int | None:
        values = tuple(statement.compile().params.values())
        email = next(value for value in values if isinstance(value, str))
        excluded_user_id = next(value for value in values if isinstance(value, int))
        return next(
            (
                user.id
                for user in self.users
                if user.email.lower() == email and user.id != excluded_user_id
            ),
            None,
        )

    def get(self, model: type[User], user_id: int) -> User | None:
        assert model is User
        return next((user for user in self.users if user.id == user_id), None)

    def add_user(
        self,
        *,
        email: str = "ada@example.com",
        first_name: str = "Ada",
        last_name: str = "Lovelace",
        phone: str | None = "+48123123123",
        birth_date: date | None = date(1815, 12, 10),
    ) -> User:
        user = User(
            id=len(self.users) + 1,
            email=email,
            password_hash="password-hash",
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            birth_date=birth_date,
            role=UserRole.CLIENT,
            is_active=True,
        )
        self.users.append(user)
        return user

    def commit(self) -> None:
        if self.duplicate_on_commit:
            raise IntegrityError("UPDATE users", {}, DuplicateEmailViolation())

    def rollback(self) -> None:
        self.rollback_calls += 1

    def refresh(self, user: User) -> None:
        assert user in self.users


@pytest.fixture(autouse=True)
def jwt_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "jwt_secret_key", SecretStr(TEST_JWT_SECRET))
    monkeypatch.setattr(security.settings, "jwt_algorithm", "HS256")
    monkeypatch.setattr(security.settings, "access_token_expire_minutes", 15)


@pytest.fixture
def user_session() -> InMemoryUserSession:
    return InMemoryUserSession()


@pytest.fixture
def client(user_session: InMemoryUserSession) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[InMemoryUserSession]:
        yield user_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _authorization_header(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {security.create_access_token(user_id)}"}


def test_get_current_user_profile_returns_authenticated_users_profile(
    client: TestClient, user_session: InMemoryUserSession
) -> None:
    user = user_session.add_user()

    response = client.get("/api/v1/users/me", headers=_authorization_header(user.id))

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "ada@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "phone": "+48123123123",
        "birth_date": "1815-12-10",
        "role": "client",
    }
    assert "password_hash" not in response.json()
    assert "is_active" not in response.json()


def test_get_current_user_profile_rejects_unauthenticated_requests(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_update_current_user_profile_updates_all_allowed_fields(
    client: TestClient, user_session: InMemoryUserSession
) -> None:
    user = user_session.add_user()

    response = client.patch(
        "/api/v1/users/me",
        headers=_authorization_header(user.id),
        json={
            "email": "ada.lovelace@example.com",
            "first_name": "Augusta",
            "last_name": "King",
            "phone": "+380501234567",
            "birth_date": "1815-12-11",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "ada.lovelace@example.com",
        "first_name": "Augusta",
        "last_name": "King",
        "phone": "+380501234567",
        "birth_date": "1815-12-11",
        "role": "client",
    }
    assert user.email == "ada.lovelace@example.com"
    assert user.first_name == "Augusta"
    assert user.last_name == "King"
    assert user.phone == "+380501234567"
    assert user.birth_date == date(1815, 12, 11)


def test_update_current_user_profile_preserves_omitted_fields(
    client: TestClient, user_session: InMemoryUserSession
) -> None:
    user = user_session.add_user()

    response = client.patch(
        "/api/v1/users/me",
        headers=_authorization_header(user.id),
        json={"first_name": "Augusta"},
    )

    assert response.status_code == 200
    assert user.first_name == "Augusta"
    assert user.email == "ada@example.com"
    assert user.last_name == "Lovelace"
    assert user.phone == "+48123123123"
    assert user.birth_date == date(1815, 12, 10)


def test_update_current_user_profile_rejects_unauthenticated_requests(client: TestClient) -> None:
    response = client.patch("/api/v1/users/me", json={"first_name": "Augusta"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_update_current_user_profile_cannot_modify_another_users_profile(
    client: TestClient, user_session: InMemoryUserSession
) -> None:
    current_user = user_session.add_user()
    other_user = user_session.add_user(email="grace@example.com", first_name="Grace")

    response = client.patch(
        "/api/v1/users/me",
        headers=_authorization_header(current_user.id),
        json={"first_name": "Augusta"},
    )

    assert response.status_code == 200
    assert current_user.first_name == "Augusta"
    assert other_user.first_name == "Grace"


@pytest.mark.parametrize(
    "payload",
    [
        {"first_name": " "},
        {"email": "not-an-email"},
        {"role": "admin"},
        {"id": 2},
        {"is_active": False},
        {"membership_status": "active"},
    ],
)
def test_update_current_user_profile_rejects_invalid_or_protected_fields(
    client: TestClient,
    user_session: InMemoryUserSession,
    payload: dict[str, object],
) -> None:
    user = user_session.add_user()

    response = client.patch(
        "/api/v1/users/me", headers=_authorization_header(user.id), json=payload
    )

    assert response.status_code == 422


def test_update_current_user_profile_rejects_duplicate_email(
    client: TestClient, user_session: InMemoryUserSession
) -> None:
    user = user_session.add_user()
    user_session.add_user(email="grace@example.com", first_name="Grace")

    response = client.patch(
        "/api/v1/users/me",
        headers=_authorization_header(user.id),
        json={"email": "GRACE@example.com"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered."}


def test_update_current_user_profile_handles_concurrent_duplicate_email(
    client: TestClient, user_session: InMemoryUserSession
) -> None:
    user = user_session.add_user()
    user_session.duplicate_on_commit = True

    response = client.patch(
        "/api/v1/users/me",
        headers=_authorization_header(user.id),
        json={"email": "ada.lovelace@example.com"},
    )

    assert response.status_code == 409
    assert user_session.rollback_calls == 1
