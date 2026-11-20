from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.membership_type import MembershipType
from app.schemas.memberships import MembershipTypeResponse

router = APIRouter(prefix="/membership-types", tags=["membership-types"])


@router.get("", response_model=list[MembershipTypeResponse])
def list_membership_types(
    db: Annotated[Session, Depends(get_db)],
) -> list[MembershipTypeResponse]:
    membership_types = db.scalars(
        select(MembershipType)
        .where(MembershipType.is_active.is_(True))
        .order_by(MembershipType.name)
    ).all()
    return [
        MembershipTypeResponse.model_validate(membership_type)
        for membership_type in membership_types
    ]
