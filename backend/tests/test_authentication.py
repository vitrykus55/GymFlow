from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core import security
from app.db.session import get_db
from app.main import app
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.enums import UserRole
from app.models.user import User

TEST_JWT_SECRET = "test-jwt-secret-key-that-is-at-least-32-characters-long"
WRONG_JWT_SECRET = "wrong-jwt-secret-key-that-is-at-least-32-characters-long"


class InMemoryAuthenticationSession:
    def __init__(self) -> None:
        self.users: list[User] = []
        self.refresh_tokens: list[AuthRefreshToken] = []
        self.pending_refresh_tokens: list[AuthRefreshToken] = []

    def scalar(self, statement: Any) -> User | AuthRefreshToken | None:
        entity = statement.column_descriptions[0]["entity"]
        value = next(iter(statement.compile().params.values()))
        if entity is User:
            return next((user for user in self.users if user.email.lower() == value), None)
        assert entity is AuthRefreshToken
        return next((token for token in self.refresh_tokens if token.token_hash == value), None)

    def get(self, model: type[User], user_id: int) -> User | None:
        assert model is User
        return next((user for user in self.users if user.id == user_id), None)

    def add(self, refresh_token: AuthRefreshToken) -> None:
        self.pending_refresh_tokens.append(refresh_token)

    def flush(self) -> None:
        self._persist_pending_refresh_tokens()

    def execute(self, statement: Any) -> None:
        parameters = statement.compile().params.values()
        family_id = next(value for value in parameters if isinstance(value, UUID))
        revoked_at = next(value for value in parameters if isinstance(value, datetime))
        for refresh_token in self.refresh_tokens:
            if refresh_token.family_id == family_id and refresh_token.revoked_at is None:
                refresh_token.revoked_at = revoked_at

    def commit(self) -> None:
        self._persist_pending_refresh_tokens()

    def rollback(self) -> None:
        self.pending_refresh_tokens.clear()

    def _persist_pending_refresh_tokens(self) -> None:
        for refresh_token in self.pending_refresh_tokens:
            refresh_token.id = len(self.refresh_tokens) + 1
            self.refresh_tokens.append(refresh_token)
        self.pending_refresh_tokens.clear()

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
    monkeypatch.setattr(security.settings, "refresh_token_expire_days", 7)
    monkeypatch.setattr(security.settings, "refresh_token_cookie_name", "gymflow_refresh_token")
    monkeypatch.setattr(security.settings, "refresh_token_cookie_path", "/api/v1/auth")
    monkeypatch.setattr(security.settings, "refresh_token_cookie_secure", False)
    monkeypatch.setattr(security.settings, "refresh_token_cookie_samesite", "lax")
    monkeypatch.setattr(security.settings, "refresh_token_cookie_domain", None)


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


def _cookie_auth_headers() -> dict[str, str]:
    return {"Origin": "http://localhost:3000"}


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
    cookie = response.headers["set-cookie"]
    assert "gymflow_refresh_token=" in cookie
    assert "HttpOnly" in cookie
    assert "Max-Age=604800" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie
    assert "expires=" in cookie.lower()
    assert len(authentication_session.refresh_tokens) == 1
    assert authentication_session.refresh_tokens[0].token_hash != response.cookies.get(
        "gymflow_refresh_token"
    )


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


def test_login_rejects_malformed_stored_password_hash(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    user = authentication_session.add_user()
    user.password_hash = "not-a-password-hash"

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}


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


def test_separate_logins_create_independent_refresh_token_families(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user()
    payload = {"email": "user@example.com", "password": "correct horse battery staple"}

    assert client.post("/api/v1/auth/login", json=payload).status_code == 200
    assert client.post("/api/v1/auth/login", json=payload).status_code == 200

    assert len(authentication_session.refresh_tokens) == 2
    assert (
        authentication_session.refresh_tokens[0].family_id
        != authentication_session.refresh_tokens[1].family_id
    )


def test_login_uses_configured_secure_refresh_cookie(
    client: TestClient,
    authentication_session: InMemoryAuthenticationSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authentication_session.add_user()
    monkeypatch.setattr(security.settings, "refresh_token_cookie_secure", True)
    monkeypatch.setattr(security.settings, "refresh_token_cookie_samesite", "strict")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]


def test_refresh_rotates_token_and_preserves_family(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )
    old_refresh_token = login_response.cookies["gymflow_refresh_token"]

    response = client.post("/api/v1/auth/refresh", headers=_cookie_auth_headers())

    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type"}
    assert response.cookies["gymflow_refresh_token"] != old_refresh_token
    assert len(authentication_session.refresh_tokens) == 2
    previous_token, replacement_token = authentication_session.refresh_tokens
    assert previous_token.revoked_at is not None
    assert previous_token.replaced_by_token_id == replacement_token.id
    assert replacement_token.family_id == previous_token.family_id
    assert all(
        old_refresh_token != token.token_hash for token in authentication_session.refresh_tokens
    )


def test_refresh_rejects_missing_unknown_expired_and_inactive_sessions(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    missing_response = client.post("/api/v1/auth/refresh")
    assert missing_response.status_code == 401
    assert "Max-Age=0" in missing_response.headers["set-cookie"]

    unknown_response = client.post(
        "/api/v1/auth/refresh",
        headers=_cookie_auth_headers(),
        cookies={"gymflow_refresh_token": "unknown-token"},
    )
    assert unknown_response.status_code == 401
    assert "Max-Age=0" in unknown_response.headers["set-cookie"]

    user = authentication_session.add_user()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )
    authentication_session.refresh_tokens[0].expires_at = datetime.now(UTC) - timedelta(seconds=1)
    expired_response = client.post("/api/v1/auth/refresh", headers=_cookie_auth_headers())
    assert expired_response.status_code == 401
    assert "Max-Age=0" in expired_response.headers["set-cookie"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )
    assert login_response.status_code == 200
    user.is_active = False
    inactive_response = client.post("/api/v1/auth/refresh", headers=_cookie_auth_headers())
    assert inactive_response.status_code == 401
    assert "Max-Age=0" in inactive_response.headers["set-cookie"]


def test_refresh_token_reuse_revokes_its_entire_family(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )
    reused_token = login_response.cookies["gymflow_refresh_token"]
    assert client.post("/api/v1/auth/refresh", headers=_cookie_auth_headers()).status_code == 200

    reuse_response = client.post(
        "/api/v1/auth/refresh",
        headers=_cookie_auth_headers(),
        cookies={"gymflow_refresh_token": reused_token},
    )

    assert reuse_response.status_code == 401
    assert "Max-Age=0" in reuse_response.headers["set-cookie"]
    assert all(token.revoked_at is not None for token in authentication_session.refresh_tokens)


def test_second_refresh_attempt_with_same_token_cannot_succeed(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )
    raw_token = login_response.cookies["gymflow_refresh_token"]

    first_response = client.post(
        "/api/v1/auth/refresh",
        headers=_cookie_auth_headers(),
        cookies={"gymflow_refresh_token": raw_token},
    )
    second_response = client.post(
        "/api/v1/auth/refresh",
        headers=_cookie_auth_headers(),
        cookies={"gymflow_refresh_token": raw_token},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 401


def test_logout_revokes_only_current_token_and_is_idempotent(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user()
    payload = {"email": "user@example.com", "password": "correct horse battery staple"}
    first_login = client.post("/api/v1/auth/login", json=payload)
    first_token = first_login.cookies["gymflow_refresh_token"]
    second_login = client.post("/api/v1/auth/login", json=payload)
    assert second_login.status_code == 200

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers=_cookie_auth_headers(),
        cookies={"gymflow_refresh_token": first_token},
    )
    repeated_logout_response = client.post(
        "/api/v1/auth/logout",
        headers=_cookie_auth_headers(),
        cookies={"gymflow_refresh_token": first_token},
    )

    assert logout_response.status_code == 204
    assert repeated_logout_response.status_code == 204
    assert "Max-Age=0" in logout_response.headers["set-cookie"]
    assert authentication_session.refresh_tokens[0].revoked_at is not None
    assert authentication_session.refresh_tokens[1].revoked_at is None


def test_logout_with_rotated_token_revokes_its_replacement(
    client: TestClient, authentication_session: InMemoryAuthenticationSession
) -> None:
    authentication_session.add_user()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )
    rotated_token = login_response.cookies["gymflow_refresh_token"]
    assert client.post("/api/v1/auth/refresh", headers=_cookie_auth_headers()).status_code == 200

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers=_cookie_auth_headers(),
        cookies={"gymflow_refresh_token": rotated_token},
    )

    assert logout_response.status_code == 204
    assert "Max-Age=0" in logout_response.headers["set-cookie"]
    assert all(token.revoked_at is not None for token in authentication_session.refresh_tokens)


def test_logout_without_cookie_succeeds_and_cookie_endpoints_require_valid_origin(
    client: TestClient,
) -> None:
    logout_response = client.post("/api/v1/auth/logout")
    invalid_origin_response = client.post(
        "/api/v1/auth/refresh", headers={"Origin": "https://untrusted.example"}
    )

    assert logout_response.status_code == 204
    assert "Max-Age=0" in logout_response.headers["set-cookie"]
    assert invalid_origin_response.status_code == 403


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
