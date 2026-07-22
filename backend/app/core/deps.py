import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import ACCESS_TOKEN, decode_token
from app.models.enums import UserRole
from app.models.user import SellerProfile, User

# auto_error=False so we can return a clean 401 (instead of FastAPI's default)
# and reuse a single credentials extractor across routes.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != ACCESS_TOKEN:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_seller(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SellerProfile:
    """Guard for seller-only routes; returns the caller's SellerProfile."""
    if user.role not in (UserRole.SELLER, UserRole.ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seller role required")
    profile = session.exec(select(SellerProfile).where(SellerProfile.user_id == user.id)).first()
    if profile is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No seller profile for this user")
    return profile
