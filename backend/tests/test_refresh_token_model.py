from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    select,
)
from sqlalchemy import Uuid as SQLAlchemyUuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password, hash_refresh_token
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.enums import UserRole
from app.models.user import User


@pytest.fixture
def refresh_token_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    metadata = MetaData()
    Table(
        "users",
        metadata,
        Column("id", BigInteger, primary_key=True),
        Column("email", String(255), nullable=False),
        Column("password_hash", String(255), nullable=False),
        Column("first_name", String(100), nullable=False),
        Column("last_name", String(100), nullable=False),
        Column("phone", String(30)),
        Column("birth_date", Date),
        Column("role", String(20), nullable=False),
        Column("is_active", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "auth_refresh_tokens",
        metadata,
        Column("id", BigInteger, primary_key=True),
        Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        Column("token_hash", String(64), nullable=False, unique=True),
        Column("family_id", SQLAlchemyUuid, nullable=False),
        Column("expires_at", DateTime(timezone=True), nullable=False),
        Column("revoked_at", DateTime(timezone=True)),
        Column(
            "replaced_by_token_id",
            BigInteger,
            ForeignKey("auth_refresh_tokens.id", ondelete="SET NULL"),
        ),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    metadata.create_all(engine)

    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        now = datetime.now(UTC)
        session.add(
            User(
                id=1,
                email="user@example.com",
                password_hash=hash_password("correct horse battery staple"),
                first_name="Ada",
                last_name="Lovelace",
                role=UserRole.CLIENT,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_token(
    *,
    token_id: int,
    token_hash: str,
    family_id: UUID,
    replaced_by_token_id: int | None = None,
) -> AuthRefreshToken:
    now = datetime.now(UTC)
    return AuthRefreshToken(
        id=token_id,
        user_id=1,
        token_hash=token_hash,
        family_id=family_id,
        expires_at=now + timedelta(days=30),
        replaced_by_token_id=replaced_by_token_id,
        created_at=now,
    )


def test_refresh_token_persists_with_user_family_and_timestamps(
    refresh_token_session: Session,
) -> None:
    family_id = uuid4()
    token = _make_token(token_id=1, token_hash=hash_refresh_token("raw-token"), family_id=family_id)
    refresh_token_session.add(token)
    refresh_token_session.commit()
    refresh_token_session.expire_all()

    stored_token = refresh_token_session.get(AuthRefreshToken, 1)

    assert stored_token is not None
    assert stored_token.user_id == 1
    assert stored_token.user.email == "user@example.com"
    assert stored_token.family_id == family_id
    assert stored_token.expires_at > datetime.now(UTC).replace(tzinfo=None)
    assert stored_token.revoked_at is None

    revoked_at = datetime.now(UTC)
    stored_token.revoked_at = revoked_at
    refresh_token_session.commit()
    refresh_token_session.expire(stored_token)

    assert stored_token.revoked_at == revoked_at.replace(tzinfo=None)


def test_refresh_token_hash_is_unique(refresh_token_session: Session) -> None:
    token_hash = hash_refresh_token("raw-token")
    refresh_token_session.add(_make_token(token_id=1, token_hash=token_hash, family_id=uuid4()))
    refresh_token_session.commit()
    refresh_token_session.add(_make_token(token_id=2, token_hash=token_hash, family_id=uuid4()))

    with pytest.raises(IntegrityError):
        refresh_token_session.commit()


def test_refresh_token_supports_self_reference(refresh_token_session: Session) -> None:
    family_id = uuid4()
    replacement = _make_token(
        token_id=2, token_hash=hash_refresh_token("replacement-token"), family_id=family_id
    )
    refresh_token_session.add(replacement)
    refresh_token_session.commit()
    original = _make_token(
        token_id=1,
        token_hash=hash_refresh_token("original-token"),
        family_id=family_id,
        replaced_by_token_id=replacement.id,
    )
    refresh_token_session.add(original)
    refresh_token_session.commit()
    refresh_token_session.expire_all()

    stored_original = refresh_token_session.get(AuthRefreshToken, original.id)

    assert stored_original is not None
    assert stored_original.replaced_by_token_id == replacement.id
    assert stored_original.replaced_by_token is not None
    assert stored_original.replaced_by_token.id == replacement.id


def test_refresh_token_requires_existing_user(refresh_token_session: Session) -> None:
    token = _make_token(token_id=1, token_hash=hash_refresh_token("raw-token"), family_id=uuid4())
    token.user_id = 999
    refresh_token_session.add(token)

    with pytest.raises(IntegrityError):
        refresh_token_session.commit()


def test_raw_refresh_token_is_not_persisted(refresh_token_session: Session) -> None:
    raw_token = "opaque-refresh-token"
    token_hash = hash_refresh_token(raw_token)
    refresh_token_session.add(_make_token(token_id=1, token_hash=token_hash, family_id=uuid4()))
    refresh_token_session.commit()

    stored_hash = refresh_token_session.scalar(select(AuthRefreshToken.token_hash))

    assert raw_token not in AuthRefreshToken.__table__.c
    assert stored_hash == token_hash
    assert stored_hash != raw_token
