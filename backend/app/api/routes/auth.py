from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, validate_cookie_auth_origin
from app.core.config import settings
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
    InvalidRefreshTokenError,
    login_user,
    logout_refresh_token,
    refresh_user_session,
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
    response: Response,
) -> AccessTokenResponse:
    try:
        tokens = login_user(db, login_request)
        _set_refresh_token_cookie(response, tokens.refresh_token, tokens.refresh_token_expires_at)
        return AccessTokenResponse(access_token=tokens.access_token)
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


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    dependencies=[Depends(validate_cookie_auth_origin)],
)
def refresh(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AccessTokenResponse | JSONResponse:
    raw_refresh_token = request.cookies.get(settings.refresh_token_cookie_name)
    if raw_refresh_token is None:
        return _invalid_refresh_response()

    try:
        tokens = refresh_user_session(db, raw_refresh_token)
    except InvalidRefreshTokenError:
        return _invalid_refresh_response()

    _set_refresh_token_cookie(response, tokens.refresh_token, tokens.refresh_token_expires_at)
    return AccessTokenResponse(access_token=tokens.access_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(validate_cookie_auth_origin)],
)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    logout_refresh_token(db, request.cookies.get(settings.refresh_token_cookie_name))
    response.status_code = status.HTTP_204_NO_CONTENT
    _clear_refresh_token_cookie(response)
    return response


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)


def _set_refresh_token_cookie(response: Response, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        expires=expires_at,
        path=settings.refresh_token_cookie_path,
        domain=settings.refresh_token_cookie_domain,
        secure=bool(settings.refresh_token_cookie_secure),
        httponly=True,
        samesite=settings.refresh_token_cookie_samesite,
    )


def _clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path=settings.refresh_token_cookie_path,
        domain=settings.refresh_token_cookie_domain,
        secure=bool(settings.refresh_token_cookie_secure),
        httponly=True,
        samesite=settings.refresh_token_cookie_samesite,
    )


def _invalid_refresh_response() -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid refresh token."},
    )
    _clear_refresh_token_cookie(response)
    return response
