import pytest
from pydantic import SecretStr

from app.core import security

TEST_JWT_SECRET = "test-jwt-secret-key-that-is-at-least-32-characters-long"


@pytest.fixture(autouse=True)
def jwt_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "jwt_secret_key", SecretStr(TEST_JWT_SECRET))
    monkeypatch.setattr(security.settings, "jwt_algorithm", "HS256")
    monkeypatch.setattr(security.settings, "access_token_expire_minutes", 15)


def test_hash_password_returns_argon2id_hash() -> None:
    password = "correct horse battery staple"

    hashed_password = security.hash_password(password)

    assert hashed_password != password
    assert hashed_password.startswith("$argon2id$")


def test_verify_password_accepts_correct_password() -> None:
    hashed_password = security.hash_password("correct horse battery staple")

    assert security.verify_password("correct horse battery staple", hashed_password) is True


def test_verify_password_rejects_incorrect_password() -> None:
    hashed_password = security.hash_password("correct horse battery staple")

    assert security.verify_password("wrong password", hashed_password) is False


def test_hash_password_uses_unique_salts() -> None:
    password = "correct horse battery staple"

    assert security.hash_password(password) != security.hash_password(password)


def test_hash_refresh_token_returns_expected_sha256_digest() -> None:
    token = "opaque-refresh-token"

    token_hash = security.hash_refresh_token(token)

    assert token_hash == "862f58013a2bd2d34eba271c56252c0e69b4715133aea31b0d0ebbb1470c3d6e"
    assert len(token_hash) == 64
    assert token_hash.isalnum()
    assert security.hash_refresh_token(token) == token_hash


def test_generate_refresh_token_returns_url_safe_256_bit_secret() -> None:
    token = security.generate_refresh_token()

    assert len(token) >= 43
    assert token.replace("-", "").replace("_", "").isalnum()
    assert security.generate_refresh_token() != token


def test_create_and_decode_access_token() -> None:
    token = security.create_access_token(user_id=42)

    payload = security.decode_access_token(token)

    assert payload["sub"] == "42"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_access_token_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "access_token_expire_minutes", -1)
    token = security.create_access_token(user_id=42)

    with pytest.raises(security.InvalidAccessTokenError, match="Invalid access token"):
        security.decode_access_token(token)


def test_decode_access_token_rejects_token_with_incorrect_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = security.create_access_token(user_id=42)
    monkeypatch.setattr(
        security.settings,
        "jwt_secret_key",
        SecretStr("another-test-secret-key-that-is-at-least-32-characters-long"),
    )

    with pytest.raises(security.InvalidAccessTokenError, match="Invalid access token"):
        security.decode_access_token(token)


def test_decode_access_token_rejects_malformed_token() -> None:
    with pytest.raises(security.InvalidAccessTokenError, match="Invalid access token"):
        security.decode_access_token("not-a-jwt")
