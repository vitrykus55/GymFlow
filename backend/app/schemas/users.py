from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.phone import normalize_phone_number
from app.models.enums import UserRole


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    birth_date: date | None
    role: UserRole


class UpdateUserProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    birth_date: date | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email", "first_name", "last_name")
    @classmethod
    def reject_null_required_fields(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("This field cannot be null.")
        return value

    @field_validator("first_name", "last_name", "phone", mode="before")
    @classmethod
    def strip_text_fields(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone_number(value) if value is not None else None
