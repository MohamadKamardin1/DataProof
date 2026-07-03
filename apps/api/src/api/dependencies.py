"""Auth dependencies: current user, workspace scoping, plan-limit enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException
from sqlalchemy import func, select

from api.auth import get_current_user
from api.database import get_session
from api.models.billing import PLAN_LIMITS, UsageRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from api.models.auth import User


async def get_current_workspace_id(
    user: User = Depends(get_current_user),
) -> int:
    if user.active_workspace_id is None:
        raise HTTPException(status_code=400, detail="No active workspace")
    return user.active_workspace_id


async def check_plan_limit(
    metric: str,
    workspace_id: int,
    session: AsyncSession,
) -> dict:
    """Check if the workspace has remaining quota for a given metric.

    Returns {'allowed': True/False, 'used': N, 'limit': N or None}.
    """
    from api.models.auth import Workspace

    result = await session.execute(
        select(Workspace.plan).where(Workspace.id == workspace_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    plan = row

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    limit = limits.get(metric)

    if limit is None:
        return {"allowed": True, "used": 0, "limit": None}

    since = datetime.now(UTC) - timedelta(days=30)
    count_result = await session.execute(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.workspace_id == workspace_id,
            UsageRecord.metric == metric,
            UsageRecord.recorded_at >= since,
        )
    )
    used = count_result.scalar() or 0

    return {"allowed": used < limit, "used": used, "limit": limit}


def enforce_plan_limit(metric: str):
    """Dependency factory: enforces plan limit for the given metric."""

    async def _check(
        workspace_id: int = Depends(get_current_workspace_id),
        session: "AsyncSession" = Depends(get_session),
    ) -> None:
        status = await check_plan_limit(metric, workspace_id, session)
        if not status["allowed"]:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Plan limit reached for {metric}: "
                    f"{status['used']}/{status['limit']}. Upgrade to continue."
                ),
            )

    return _check


def record_usage(metric: str):
    """Dependency factory that records usage after a successful request."""

    async def _record(
        workspace_id: int = Depends(get_current_workspace_id),
        session: "AsyncSession" = Depends(get_session),
    ) -> None:
        session.add(UsageRecord(workspace_id=workspace_id, metric=metric))

    return _record
