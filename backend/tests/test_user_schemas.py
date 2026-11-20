from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.users import UpdateUserProfileRequest


def test_profile_update_schema_preserves_only_explicitly_provided_fields() -> None:
    profile_update = UpdateUserProfileRequest.model_validate({"first_name": " Ada "})

    assert profile_update.first_name == "Ada"
    assert profile_update.model_dump(exclude_unset=True) == {"first_name": "Ada"}


def test_profile_update_schema_normalizes_email_and_allows_nullable_profile_fields() -> None:
    profile_update = UpdateUserProfileRequest.model_validate(
        {
            "email": " User@Example.COM ",
            "phone": None,
            "birth_date": None,
        }
    )

    assert profile_update.email == "user@example.com"
    assert profile_update.phone is None
    assert profile_update.birth_date is None
    assert profile_update.model_dump(exclude_unset=True) == {
        "email": "user@example.com",
        "phone": None,
        "birth_date": None,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"first_name": " "},
        {"last_name": " "},
        {"first_name": "A" * 101},
        {"email": "not-an-email"},
        {"role": "admin"},
        {"id": 1},
        {"is_active": False},
        {"membership_status": "active"},
    ],
)
def test_profile_update_schema_rejects_invalid_or_protected_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        UpdateUserProfileRequest.model_validate(payload)


def test_profile_update_schema_parses_birth_date() -> None:
    profile_update = UpdateUserProfileRequest.model_validate({"birth_date": "1815-12-10"})

    assert profile_update.birth_date == date(1815, 12, 10)
