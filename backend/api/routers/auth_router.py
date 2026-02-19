"""Authentication endpoints: login, refresh, me, logout."""

import os

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
limiter = Limiter(key_func=get_remote_address)

from api.auth import (
    create_access_token,
    create_refresh_token,
    _decode_token,
    get_current_user,
    JWT_REFRESH_EXPIRY_DAYS,
)
from api.schemas import LoginRequest, LoginResponse, UserInfo
from src.user_store import User

router = APIRouter()

REFRESH_COOKIE = "refresh_token"


def _build_features() -> dict:
    """Build feature flags from env vars. Read per-request so changes take effect without restart."""
    features: dict = {}
    if os.environ.get("CLIENT_DOCUMENT_VIEW", "").lower() == "true":
        features["client_document_view"] = True
    return features


def _user_info(user: "User") -> UserInfo:
    return UserInfo(id=user.id, email=user.email, role=user.role, features=_build_features())


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, response: Response, body: LoginRequest):
    """Authenticate user, return access token + set refresh cookie."""
    user_store = request.app.state.user_store
    user = user_store.get_by_email(body.email)

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user_store.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/api/auth/refresh",
        max_age=JWT_REFRESH_EXPIRY_DAYS * 86400,
    )

    return LoginResponse(
        access_token=access_token,
        user=_user_info(user),
    )


@router.post("/refresh", response_model=LoginResponse)
@limiter.limit("10/minute")
async def refresh(request: Request, response: Response):
    """Issue new access token from refresh cookie."""
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = _decode_token(refresh_token, "refresh")
    user_id = payload.get("sub")

    user_store = request.app.state.user_store
    user = user_store.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token(user.id, user.role)

    return LoginResponse(
        access_token=access_token,
        user=_user_info(user),
    )


@router.get("/me", response_model=UserInfo)
async def me(user: User = Depends(get_current_user)):
    """Return current user info."""
    return _user_info(user)


@router.post("/logout")
async def logout(response: Response):
    """Clear refresh cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path="/api/auth/refresh",
    )
    return {"success": True}
