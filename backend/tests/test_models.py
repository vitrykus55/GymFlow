import pytest
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.dialects.postgresql import ENUM, dialect
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateIndex

from app.db.base import Base
from app.models import (
    AuthRefreshToken,
    Booking,
    CheckIn,
    ClassSession,
    ClassType,
    Membership,
    MembershipType,
    Payment,
    User,
)


def _constraint_names(table_name: str, constraint_type: type[object]) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type) and constraint.name is not None
    }


def test_all_model_mappers_configure_successfully() -> None:
    configure_mappers()

    assert {mapper.class_ for mapper in Base.registry.mappers} == {
        User,
        AuthRefreshToken,
        MembershipType,
        Membership,
        Payment,
        ClassType,
        ClassSession,
        Booking,
        CheckIn,
    }


def test_expected_tables_and_primary_keys_are_registered() -> None:
    expected_tables = {
        "users",
        "auth_refresh_tokens",
        "membership_types",
        "memberships",
        "payments",
        "class_types",
        "class_sessions",
        "bookings",
        "check_ins",
    }

    assert set(Base.metadata.tables) == expected_tables
    for table_name in expected_tables:
        assert list(Base.metadata.tables[table_name].primary_key.columns.keys()) == ["id"]
        assert isinstance(Base.metadata.tables[table_name].c.id.type, BigInteger)


@pytest.mark.parametrize(
    ("table_name", "column_name", "column_type", "nullable", "length"),
    [
        ("users", "email", String, False, 255),
        ("users", "phone", String, True, 30),
        ("users", "birth_date", Date, True, None),
        ("users", "is_active", Boolean, False, None),
        ("auth_refresh_tokens", "token_hash", String, False, 64),
        ("auth_refresh_tokens", "expires_at", DateTime, False, None),
        ("auth_refresh_tokens", "revoked_at", DateTime, True, None),
        ("auth_refresh_tokens", "replaced_by_token_id", BigInteger, True, None),
        ("class_types", "duration_minutes", Integer, False, None),
        ("class_sessions", "room", String, True, 50),
        ("class_sessions", "capacity", Integer, False, None),
        ("membership_types", "duration_days", Integer, False, None),
        ("membership_types", "max_entries", Integer, True, None),
        ("memberships", "start_date", Date, False, None),
        ("payments", "currency", String, False, 3),
        ("check_ins", "membership_id", BigInteger, True, None),
    ],
)
def test_important_columns_preserve_types_and_nullability(
    table_name: str,
    column_name: str,
    column_type: type[object],
    nullable: bool,
    length: int | None,
) -> None:
    column = Base.metadata.tables[table_name].c[column_name]

    assert isinstance(column.type, column_type)
    assert column.nullable is nullable
    if length is not None:
        assert column.type.length == length


def test_numeric_columns_preserve_precision_and_scale() -> None:
    membership_price = Base.metadata.tables["membership_types"].c.price
    payment_amount = Base.metadata.tables["payments"].c.amount

    for column in (membership_price, payment_amount):
        assert isinstance(column.type, Numeric)
        assert (column.type.precision, column.type.scale) == (10, 2)
        assert column.nullable is False


def test_timestamp_columns_are_timezone_aware() -> None:
    timestamp_columns = (
        ("users", "created_at"),
        ("users", "updated_at"),
        ("auth_refresh_tokens", "expires_at"),
        ("auth_refresh_tokens", "revoked_at"),
        ("auth_refresh_tokens", "created_at"),
        ("class_sessions", "starts_at"),
        ("class_sessions", "ends_at"),
        ("bookings", "created_at"),
        ("bookings", "cancelled_at"),
        ("check_ins", "checked_in_at"),
        ("check_ins", "checked_out_at"),
        ("payments", "paid_at"),
    )

    for table_name, column_name in timestamp_columns:
        column = Base.metadata.tables[table_name].c[column_name]
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True


@pytest.mark.parametrize(
    ("table_name", "column_name", "enum_name", "values"),
    [
        ("users", "role", "user_role", ["client", "trainer", "admin"]),
        ("memberships", "status", "membership_status", ["active", "expired", "cancelled"]),
        ("payments", "status", "payment_status", ["pending", "paid", "failed", "refunded"]),
        ("payments", "method", "payment_method", ["card", "cash", "transfer", "simulated"]),
        (
            "bookings",
            "status",
            "booking_status",
            ["confirmed", "waitlist", "cancelled", "attended", "no_show"],
        ),
        ("check_ins", "method", "checkin_method", ["qr", "manual", "card"]),
    ],
)
def test_postgresql_enums_preserve_names_and_values(
    table_name: str, column_name: str, enum_name: str, values: list[str]
) -> None:
    enum_type = Base.metadata.tables[table_name].c[column_name].type

    assert isinstance(enum_type, ENUM)
    assert enum_type.name == enum_name
    assert enum_type.enums == values
    assert enum_type.create_type is False


@pytest.mark.parametrize(
    ("source_model", "relationship_name", "target_model", "back_populates"),
    [
        (User, "bookings", Booking, "user"),
        (User, "memberships", Membership, "user"),
        (User, "payments", Payment, "user"),
        (User, "check_ins", CheckIn, "user"),
        (User, "refresh_tokens", AuthRefreshToken, "user"),
        (AuthRefreshToken, "user", User, "refresh_tokens"),
        (User, "class_sessions_as_trainer", ClassSession, "trainer"),
        (ClassType, "class_sessions", ClassSession, "class_type"),
        (ClassSession, "class_type", ClassType, "class_sessions"),
        (ClassSession, "trainer", User, "class_sessions_as_trainer"),
        (ClassSession, "bookings", Booking, "class_session"),
        (Booking, "class_session", ClassSession, "bookings"),
        (Booking, "user", User, "bookings"),
        (MembershipType, "memberships", Membership, "membership_type"),
        (Membership, "user", User, "memberships"),
        (Membership, "membership_type", MembershipType, "memberships"),
        (Membership, "payments", Payment, "membership"),
        (Membership, "check_ins", CheckIn, "membership"),
        (Payment, "user", User, "payments"),
        (Payment, "membership", Membership, "payments"),
        (CheckIn, "user", User, "check_ins"),
        (CheckIn, "membership", Membership, "check_ins"),
    ],
)
def test_relationships_have_expected_back_populates(
    source_model: type[object],
    relationship_name: str,
    target_model: type[object],
    back_populates: str,
) -> None:
    relationship = inspect(source_model).relationships[relationship_name]

    assert relationship.mapper.class_ is target_model
    assert relationship.back_populates == back_populates


def test_foreign_keys_reference_expected_columns_and_on_delete_actions() -> None:
    expected_foreign_keys = {
        "bookings_session_id_fkey": ("bookings", "session_id", "class_sessions.id", "CASCADE"),
        "bookings_user_id_fkey": ("bookings", "user_id", "users.id", "CASCADE"),
        "check_ins_membership_id_fkey": (
            "check_ins",
            "membership_id",
            "memberships.id",
            "SET NULL",
        ),
        "check_ins_user_id_fkey": ("check_ins", "user_id", "users.id", "CASCADE"),
        "auth_refresh_tokens_user_id_fkey": (
            "auth_refresh_tokens",
            "user_id",
            "users.id",
            "CASCADE",
        ),
        "auth_refresh_tokens_replaced_by_token_id_fkey": (
            "auth_refresh_tokens",
            "replaced_by_token_id",
            "auth_refresh_tokens.id",
            "SET NULL",
        ),
        "class_sessions_class_type_id_fkey": (
            "class_sessions",
            "class_type_id",
            "class_types.id",
            None,
        ),
        "class_sessions_trainer_id_fkey": ("class_sessions", "trainer_id", "users.id", None),
        "memberships_membership_type_id_fkey": (
            "memberships",
            "membership_type_id",
            "membership_types.id",
            None,
        ),
        "memberships_user_id_fkey": ("memberships", "user_id", "users.id", "CASCADE"),
        "payments_membership_id_fkey": ("payments", "membership_id", "memberships.id", "SET NULL"),
        "payments_user_id_fkey": ("payments", "user_id", "users.id", None),
    }

    actual_foreign_keys = {
        foreign_key.constraint.name: (
            foreign_key.parent.table.name,
            foreign_key.parent.name,
            foreign_key.target_fullname,
            foreign_key.ondelete,
        )
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
    }

    assert actual_foreign_keys == expected_foreign_keys


@pytest.mark.parametrize(
    ("table_name", "expected_constraints", "constraint_type"),
    [
        ("bookings", {"ux_booking_session_user"}, UniqueConstraint),
        ("class_types", {"class_types_name_key"}, UniqueConstraint),
        ("membership_types", {"membership_types_name_key"}, UniqueConstraint),
        ("check_ins", {"ck_checkout_after_checkin"}, CheckConstraint),
        ("class_sessions", {"ck_session_capacity", "ck_session_time"}, CheckConstraint),
        (
            "class_types",
            {"ck_class_types_capacity", "ck_class_types_duration"},
            CheckConstraint,
        ),
        (
            "membership_types",
            {
                "ck_membership_types_duration",
                "ck_membership_types_entries",
                "ck_membership_types_price",
            },
            CheckConstraint,
        ),
        ("memberships", {"ck_membership_dates"}, CheckConstraint),
        ("payments", {"ck_payments_amount"}, CheckConstraint),
        ("auth_refresh_tokens", {"uq_auth_refresh_tokens_token_hash"}, UniqueConstraint),
    ],
)
def test_named_constraints_are_registered(
    table_name: str, expected_constraints: set[str], constraint_type: type[object]
) -> None:
    assert expected_constraints <= _constraint_names(table_name, constraint_type)


def test_important_indexes_and_functional_email_index_are_registered() -> None:
    expected_indexes = {
        "bookings": {"ix_bookings_session", "ix_bookings_user_id"},
        "check_ins": {"ix_check_ins_checked_in_at", "ix_check_ins_user_time"},
        "class_sessions": {"ix_class_sessions_starts_at", "ix_class_sessions_trainer"},
        "memberships": {"ix_memberships_status_end", "ix_memberships_user_id"},
        "payments": {"ix_payments_paid_at", "ix_payments_user_id"},
        "users": {"ix_users_role", "ux_users_email_lower"},
        "auth_refresh_tokens": {
            "ix_auth_refresh_tokens_expires_at",
            "ix_auth_refresh_tokens_family_id",
            "ix_auth_refresh_tokens_user_id",
        },
    }

    for table_name, expected_names in expected_indexes.items():
        actual_names = {index.name for index in Base.metadata.tables[table_name].indexes}
        assert actual_names == expected_names

    email_index = next(
        index
        for index in Base.metadata.tables["users"].indexes
        if index.name == "ux_users_email_lower"
    )
    email_index_ddl = str(CreateIndex(email_index).compile(dialect=dialect()))

    assert email_index.unique is True
    assert "lower((email)::text)" in email_index_ddl
