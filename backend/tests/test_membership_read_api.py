from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core import security
from app.db.session import get_db
from app.main import app
from app.models.enums import MembershipStatus, UserRole
from app.models.membership import Membership
from app.models.membership_type import MembershipType
from app.models.user import User

TEST_JWT_SECRET = "test-jwt-secret-key-that-is-at-least-32-characters-long"


class InMemoryMembershipSession:
    def __init__(self) -> None:
        self.users: list[User] = []
        self.membership_types: list[MembershipType] = []
        self.memberships: list[Membership] = []

    def get(self, model: type[User], user_id: int) -> User | None:
        assert model is User
        return next((user for user in self.users if user.id == user_id), None)

    def scalars(self, statement: Any) -> "InMemoryScalarResult":
        active_membership_types = [
            membership_type
            for membership_type in self.membership_types
            if membership_type.is_active
        ]
        return InMemoryScalarResult(active_membership_types)

    def scalar(self, statement: Any) -> Membership | int | None:
        user_id = next(
            (
                value
                for value in statement.compile().params.values()
                if isinstance(value, int) and any(user.id == value for user in self.users)
            ),
            None,
        )
        user_memberships = [
            membership for membership in self.memberships if membership.user_id == user_id
        ]
        if statement._with_options:
            return max(user_memberships, key=lambda membership: membership.id, default=None)

        now = datetime.now(UTC)
        return next(
            (
                membership.id
                for membership in user_memberships
                if membership.membership_type.code == "coach"
                and membership.status is MembershipStatus.ACTIVE
                and membership.starts_at <= now < membership.expires_at
            ),
            None,
        )

    def add_user(self, *, email: str) -> User:
        user = User(
            id=len(self.users) + 1,
            email=email,
            password_hash="password-hash",
            first_name="Ada",
            last_name="Lovelace",
            role=UserRole.CLIENT,
            is_active=True,
        )
        self.users.append(user)
        return user

    def add_membership_type(self, *, code: str, is_active: bool = True) -> MembershipType:
        membership_type = MembershipType(
            id=len(self.membership_types) + 1,
            code=code,
            name=f"{code.title()} Membership",
            description=None,
            duration_days=None,
            price=None,
            max_entries=None,
            is_active=is_active,
        )
        self.membership_types.append(membership_type)
        return membership_type

    def add_membership(
        self,
        *,
        user: User,
        membership_type: MembershipType,
        status: MembershipStatus = MembershipStatus.ACTIVE,
    ) -> Membership:
        now = datetime.now(UTC)
        membership = Membership(
            id=len(self.memberships) + 1,
            user_id=user.id,
            membership_type_id=membership_type.id,
            membership_type=membership_type,
            starts_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=1),
            status=status,
        )
        self.memberships.append(membership)
        return membership


class InMemoryScalarResult:
    def __init__(self, values: list[MembershipType]) -> None:
        self.values = values

    def all(self) -> list[MembershipType]:
        return self.values


@pytest.fixture(autouse=True)
def jwt_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "jwt_secret_key", SecretStr(TEST_JWT_SECRET))
    monkeypatch.setattr(security.settings, "jwt_algorithm", "HS256")
    monkeypatch.setattr(security.settings, "access_token_expire_minutes", 15)


@pytest.fixture
def membership_session() -> InMemoryMembershipSession:
    return InMemoryMembershipSession()


@pytest.fixture
def client(membership_session: InMemoryMembershipSession) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[InMemoryMembershipSession]:
        yield membership_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _authorization_header(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {security.create_access_token(user_id)}"}


def test_list_membership_types_returns_only_active_types(
    client: TestClient, membership_session: InMemoryMembershipSession
) -> None:
    membership_session.add_membership_type(code="coach")
    membership_session.add_membership_type(code="retired", is_active=False)

    response = client.get("/api/v1/membership-types")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "code": "coach",
            "name": "Coach Membership",
            "description": None,
            "duration_days": None,
            "price": None,
            "max_entries": None,
        }
    ]


def test_get_current_membership_returns_authenticated_users_membership(
    client: TestClient, membership_session: InMemoryMembershipSession
) -> None:
    current_user = membership_session.add_user(email="ada@example.com")
    other_user = membership_session.add_user(email="grace@example.com")
    coach_type = membership_session.add_membership_type(code="coach")
    membership_session.add_membership(user=current_user, membership_type=coach_type)
    membership_session.add_membership(user=other_user, membership_type=coach_type)

    response = client.get(
        "/api/v1/users/me/membership", headers=_authorization_header(current_user.id)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["membership"]["id"] == 1
    assert body["membership"]["membership_type"]["code"] == "coach"
    assert body["membership"]["status"] == "active"
    assert body["has_active_coach_membership"] is True


def test_get_current_membership_returns_null_without_membership(
    client: TestClient, membership_session: InMemoryMembershipSession
) -> None:
    user = membership_session.add_user(email="ada@example.com")

    response = client.get("/api/v1/users/me/membership", headers=_authorization_header(user.id))

    assert response.status_code == 200
    assert response.json() == {"membership": None, "has_active_coach_membership": False}


def test_get_current_membership_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me/membership")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_membership_activation_is_not_exposed_as_a_public_api(client: TestClient) -> None:
    response = client.post("/api/v1/memberships/activate")

    assert response.status_code == 404


def test_profile_update_rejects_attempt_to_grant_coach_role(
    client: TestClient, membership_session: InMemoryMembershipSession
) -> None:
    user = membership_session.add_user(email="ada@example.com")

    response = client.patch(
        "/api/v1/users/me",
        headers=_authorization_header(user.id),
        json={"role": "coach"},
    )

    assert response.status_code == 422
