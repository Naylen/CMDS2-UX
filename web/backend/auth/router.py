"""Authentication endpoints and middleware."""

from __future__ import annotations

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
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    await _ensure_admin(db)
    result = await db.execute(
        select(UserRecord).where(UserRecord.username == body.username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user.username)
    refresh = create_refresh_token(user.username)

    response.set_cookie(
        "access_token", access, httponly=True, samesite="strict", secure=True, max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        "refresh_token", refresh, httponly=True, samesite="strict", secure=True, max_age=settings.refresh_token_expire_days * 86400,
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
        "access_token", access, httponly=True, samesite="strict", secure=True, max_age=settings.access_token_expire_minutes * 60,
    )
    return TokenResponse(access_token=access)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.get("/me", response_model=UserInfo)
async def me(user: str = Depends(get_current_user)):
    return UserInfo(username=user)
