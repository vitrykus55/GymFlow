from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import MembershipStatus


class MembershipTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    duration_days: int | None
    price: Decimal | None
    max_entries: int | None


class UserMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: MembershipStatus
    starts_at: datetime
    expires_at: datetime
    membership_type: MembershipTypeResponse


class CurrentMembershipResponse(BaseModel):
    membership: UserMembershipResponse | None
    has_active_coach_membership: bool
