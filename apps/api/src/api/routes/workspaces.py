"""Workspace management routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.auth import get_current_user
from api.database import get_session
from api.models.auth import User, Workspace, WorkspaceMembership

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    slug: str
    plan: str
    role: str


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = None


@router.get("/", response_model=WorkspaceListResponse)
async def list_workspaces(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceListResponse:
    result = await session.execute(
        select(Workspace, WorkspaceMembership.role)
        .join(WorkspaceMembership, Workspace.id == WorkspaceMembership.workspace_id)
        .where(WorkspaceMembership.user_id == user.id)
    )
    rows = result.all()
    workspaces = [
        WorkspaceResponse(
            id=ws.id, name=ws.name, slug=ws.slug, plan=ws.plan, role=role
        )
        for ws, role in rows
    ]
    return WorkspaceListResponse(workspaces=workspaces)


@router.post("/", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    request: CreateWorkspaceRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceResponse:
    slug = request.name.lower().replace(" ", "-")[:100]
    workspace = Workspace(name=request.name, slug=slug, plan="free")
    session.add(workspace)
    await session.flush()

    membership = WorkspaceMembership(
        user_id=user.id, workspace_id=workspace.id, role="owner"
    )
    session.add(membership)
    await session.commit()

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        plan=workspace.plan,
        role="owner",
    )


@router.post("/{workspace_id}/switch")
async def switch_workspace(
    workspace_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # Verify membership
    result = await session.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user.id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    user.active_workspace_id = workspace_id
    await session.commit()
    return {"detail": "Workspace switched", "workspace_id": workspace_id}
