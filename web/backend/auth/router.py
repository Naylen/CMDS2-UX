"""Authentication endpoints and middleware."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from web.backend.config import settings
from web.backend.core.db import get_db
from web.backend.models.database import UserRecord
from web.backend.models.schemas import LoginRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ── Simple in-memory rate limiter ────────────────────────────────────────
# Tracks failed login attempts per IP. Locks out for LOCKOUT_SECONDS after
# MAX_ATTEMPTS consecutive failures.
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300  # 5 minutes
_failed_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str):
    """Raise 429 if too many recent failed login attempts from this IP."""
    now = time.monotonic()
    # Prune old entries
    _failed_attempts[client_ip] = [
        t for t in _failed_attempts[client_ip]
        if now - t < _LOCKOUT_SECONDS
    ]
    if len(_failed_attempts[client_ip]) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Try again in {_LOCKOUT_SECONDS // 60} minutes.",
        )


def _record_failure(client_ip: str):
    _failed_attempts[client_ip].append(time.monotonic())


def _clear_failures(client_ip: str):
    _failed_attempts.pop(client_ip, None)


# Cookie attributes — must match between set_cookie and delete_cookie
_COOKIE_ATTRS = dict(httponly=True, samesite="strict", secure=True, path="/")


async def _ensure_admin(db: AsyncSession):
    """Create default admin if no users exist."""
    result = await db.execute(select(UserRecord).limit(1))
    if result.scalar_one_or_none() is None:
        admin = UserRecord(
            username=settings.admin_user,
            password_hash=hash_password(settings.admin_password),
        )
        db.add(admin)
        await db.commit()


async def get_current_user(request: Request) -> str:
    """Extract and validate user from JWT cookie or Authorization header."""
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    await _ensure_admin(db)
    result = await db.execute(
        select(UserRecord).where(UserRecord.username == body.username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        _record_failure(client_ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _clear_failures(client_ip)
    access = create_access_token(user.username)
    refresh = create_refresh_token(user.username)

    response.set_cookie(
        "access_token", access, max_age=settings.access_token_expire_minutes * 60,
        **_COOKIE_ATTRS,
    )
    response.set_cookie(
        "refresh_token", refresh, max_age=settings.refresh_token_expire_days * 86400,
        **_COOKIE_ATTRS,
    )
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access = create_access_token(payload["sub"])
    response.set_cookie(
        "access_token", access, max_age=settings.access_token_expire_minutes * 60,
        **_COOKIE_ATTRS,
    )
    return TokenResponse(access_token=access)


@router.post("/logout")
async def logout(response: Response):
    # delete_cookie must mirror set_cookie attributes for browsers to clear
    response.delete_cookie("access_token", **_COOKIE_ATTRS)
    response.delete_cookie("refresh_token", **_COOKIE_ATTRS)
    return {"ok": True}


@router.get("/me", response_model=UserInfo)
async def me(user: str = Depends(get_current_user)):
    return UserInfo(username=user)
