from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.membership import Membership
from app.models.user import User
from app.schemas.memberships import CurrentMembershipResponse, UserMembershipResponse
from app.schemas.users import UpdateUserProfileRequest, UserProfileResponse
from app.services.auth import EmailAlreadyRegisteredError
from app.services.memberships import has_active_coach_membership
from app.services.users import update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserProfileResponse:
    return UserProfileResponse.model_validate(current_user)


@router.get("/me/membership", response_model=CurrentMembershipResponse)
def get_current_user_membership(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentMembershipResponse:
    membership = db.scalar(
        select(Membership)
        .options(joinedload(Membership.membership_type))
        .where(Membership.user_id == current_user.id)
        .order_by(Membership.created_at.desc(), Membership.id.desc())
        .limit(1)
    )
    return CurrentMembershipResponse(
        membership=(
            UserMembershipResponse.model_validate(membership) if membership is not None else None
        ),
        has_active_coach_membership=has_active_coach_membership(db, user_id=current_user.id),
    )


@router.patch("/me", response_model=UserProfileResponse)
def update_current_user_profile(
    profile_update: UpdateUserProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserProfileResponse:
    try:
        updated_user = update_user_profile(db, current_user, profile_update)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        ) from exc
    return UserProfileResponse.model_validate(updated_user)
