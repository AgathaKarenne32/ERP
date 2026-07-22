import uuid

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.security import (
    REFRESH_TOKEN,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import SellerProfile, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    # httpOnly cookie so the refresh token is never readable by JS in Angular.
    response.set_cookie(
        _REFRESH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path=f"{settings.api_prefix}/auth",
    )


def _user_out(session: Session, user: User) -> UserOut:
    seller = session.exec(select(SellerProfile).where(SellerProfile.user_id == user.id)).first()
    return UserOut(**user.model_dump(), seller_id=seller.id if seller else None)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> UserOut:
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    session.flush()

    # A seller needs a storefront; create one on registration.
    if payload.role == UserRole.SELLER:
        session.add(
            SellerProfile(
                user_id=user.id,
                store_name=payload.store_name or f"{payload.name}'s Store",
            )
        )
    session.commit()
    session.refresh(user)
    return _user_out(session, user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> TokenResponse:
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    _set_refresh_cookie(response, create_refresh_token(str(user.id)))
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    session: Session = Depends(get_session),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    try:
        claims = decode_token(refresh_token)
        if claims.get("type") != REFRESH_TOKEN:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc

    if session.get(User, user_id) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    _set_refresh_cookie(response, create_refresh_token(str(user_id)))
    return TokenResponse(access_token=create_access_token(str(user_id)))


# `/api/me` lives at the top level (not under /auth) per the API contract.
me_router = APIRouter(tags=["auth"])


@me_router.get("/me", response_model=UserOut)
def me(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserOut:
    return _user_out(session, user)
