"""Auth routes: signup, login, refresh, me."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from api.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from api.database import get_session
from api.models.auth import User, Workspace, WorkspaceMembership

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Request/Response Models ---

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = None
    workspace_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    workspace_id: int | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str | None = None
    is_active: bool
    active_workspace_id: int | None = None


# --- Endpoints ---

@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(
    request: SignupRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    existing = await session.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
    )
    session.add(user)
    await session.flush()

    ws_name = request.workspace_name or f"{request.email.split('@')[0]}'s Lab"
    slug = ws_name.lower().replace(" ", "-").replace("'", "")[:100]
    workspace = Workspace(name=ws_name, slug=slug, plan="free")
    session.add(workspace)
    await session.flush()

    membership = WorkspaceMembership(
        user_id=user.id, workspace_id=workspace.id, role="owner"
    )
    session.add(membership)

    user.active_workspace_id = workspace.id
    await session.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, workspace.id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        workspace_id=workspace.id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    ws_id = user.active_workspace_id
    return TokenResponse(
        access_token=create_access_token(user.id, ws_id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        workspace_id=ws_id,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    payload = decode_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    user_id = int(payload["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    ws_id = user.active_workspace_id
    return TokenResponse(
        access_token=create_access_token(user.id, ws_id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        workspace_id=ws_id,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        active_workspace_id=user.active_workspace_id,
    )
