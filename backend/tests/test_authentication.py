from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core import security
from app.db.session import get_db
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

TEST_JWT_SECRET = "test-jwt-secret-key-that-is-at-least-32-characters-long"
WRONG_JWT_SECRET = "wrong-jwt-secret-key-that-is-at-least-32-characters-long"


class InMemoryAuthenticationSession:
    def __init__(self) -> None:
        self.users: list[User] = []

    def scalar(self, statement: Any) -> User | None:
        email = next(iter(statement.compile().params.values()))
        return next((user for user in self.users if user.email.lower() == email), None)

    def get(self, model: type[User], user_id: int) -> User | None:
        assert model is User
        return next((user for user in self.users if user.id == user_id), None)

    def add_user(
        self,
        *,
        email: str = "user@example.com",
        password: str = "correct horse battery staple",
        is_active: bool = True,
    ) -> User:
        user = User(
            id=len(self.users) + 1,
            email=email,
            password_hash=security.hash_password(password),
            first_name="Ada",
            last_name="Lovelace",
            role=UserRole.CLIENT,
            is_active=is_active,
        )
        self.users.append(user)
        return user


@pytest.fixture(autouse=True)
def jwt_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "jwt_secret_key", SecretStr(TEST_JWT_SECRET))
    monkeypatch.setattr(security.settings, "jwt_algorithm", "HS256")
    monkeypatch.setattr(security.settings, "access_token_expire_minutes", 15)


@pytest.fixture
def authentication_session() -> InMemoryAuthenticationSession:
    return InMemoryAuthenticationSession()


@pytest.fixture
def client(authentication_session: InMemoryAuthenticationSession) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[InMemoryAuthenticationSession]:
        yield authentication_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _authorization_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_bearer_access_token_without_password_data(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type"}
    assert response.json()["token_type"] == "bearer"
    assert security.decode_access_token(response.json()["access_token"])["sub"] == "1"


def test_login_normalizes_email(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user(email="user@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": " User@Example.COM ", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200


def test_login_returns_same_error_for_unknown_email_and_incorrect_password(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user()

    incorrect_password_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "incorrect password"},
    )
    unknown_email_response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "incorrect password"},
    )

    assert incorrect_password_response.status_code == 401
    assert unknown_email_response.status_code == 401
    assert incorrect_password_response.json() == unknown_email_response.json()


def test_inactive_user_cannot_log_in(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user(is_active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive account."}


def test_me_returns_public_fields_for_valid_token(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    user = authentication_session.add_user()

    response = client.get(
        "/api/v1/auth/me", headers=_authorization_header(security.create_access_token(user.id))
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "email": "user@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "role": "client",
    }
    assert "password_hash" not in response.json()


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("token", ["not-a-jwt", "Bearer"])
def test_me_rejects_malformed_token(client: TestClient, token: str) -> None:
    response = client.get("/api/v1/auth/me", headers=_authorization_header(token))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_expired_token(client: TestClient) -> None:
    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {"sub": "1", "iat": now - timedelta(minutes=2), "exp": now - timedelta(minutes=1)},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get("/api/v1/auth/me", headers=_authorization_header(expired_token))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_token_with_invalid_signature(client: TestClient) -> None:
    now = datetime.now(UTC)
    invalid_signature_token = jwt.encode(
        {"sub": "1", "iat": now, "exp": now + timedelta(minutes=15)},
        WRONG_JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get("/api/v1/auth/me", headers=_authorization_header(invalid_signature_token))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_token_for_nonexistent_user(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me", headers=_authorization_header(security.create_access_token(999))
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_inactive_user(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    user = authentication_session.add_user(is_active=False)

    response = client.get(
        "/api/v1/auth/me", headers=_authorization_header(security.create_access_token(user.id))
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
