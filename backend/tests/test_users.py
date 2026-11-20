from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core import security
from app.db.session import get_db
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

TEST_JWT_SECRET = "test-jwt-secret-key-that-is-at-least-32-characters-long"


class InMemoryUserSession:
    def __init__(self) -> None:
        self.users: list[User] = []

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
