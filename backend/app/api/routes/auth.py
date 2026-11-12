from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterUserRequest,
    RegisterUserResponse,
)
from app.services.auth import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    login_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterUserResponse, status_code=status.HTTP_201_CREATED)
def register(
    registration: RegisterUserRequest,
    db: Annotated[Session, Depends(get_db)],
) -> RegisterUserResponse:
    try:
        return RegisterUserResponse.model_validate(register_user(db, registration))
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        ) from exc


@router.post("/login", response_model=AccessTokenResponse)
def login(
    login_request: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AccessTokenResponse:
    try:
        return AccessTokenResponse(access_token=login_user(db, login_request))
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account.",
        ) from exc


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
