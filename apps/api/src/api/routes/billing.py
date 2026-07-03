"""Stripe billing routes: checkout, webhook, portal, usage status."""

from __future__ import annotations

from typing import TYPE_CHECKING

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from api.config import settings
from api.database import get_session
from api.dependencies import check_plan_limit, get_current_workspace_id
from api.models.auth import Workspace

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = settings.stripe_secret_key


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


class UsageStatusResponse(BaseModel):
    plan: str
    limits: dict


@router.post("/checkout/{price_id}", response_model=CheckoutResponse)
async def create_checkout_session(
    price_id: str,
    workspace_id: int = Depends(get_current_workspace_id),
    session: AsyncSession = Depends(get_session),
) -> CheckoutResponse:
    result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    customer_id = workspace.stripe_customer_id
    if customer_id is None:
        customer = stripe.Customer.create(
            metadata={"workspace_id": str(workspace.id)},
        )
        customer_id = customer.id
        workspace.stripe_customer_id = customer_id
        await session.commit()

    checkout = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.app_url}/billing?success=true",
        cancel_url=f"{settings.app_url}/billing?canceled=true",
        metadata={"workspace_id": str(workspace.id)},
    )
    return CheckoutResponse(url=checkout.url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    workspace_id: int = Depends(get_current_workspace_id),
    session: AsyncSession = Depends(get_session),
) -> PortalResponse:
    result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None or workspace.stripe_customer_id is None:
        raise HTTPException(status_code=400, detail="No Stripe customer yet")

    portal = stripe.billing_portal.Session.create(
        customer=workspace.stripe_customer_id,
        return_url=f"{settings.app_url}/billing",
    )
    return PortalResponse(url=portal.url)


@router.get("/usage", response_model=UsageStatusResponse)
async def get_usage_status(
    workspace_id: int = Depends(get_current_workspace_id),
    session: AsyncSession = Depends(get_session),
) -> UsageStatusResponse:
    result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    limits = {}
    for metric in ["uploads", "analyses_run", "reports_generated"]:
        status = await check_plan_limit(metric, workspace_id, session)
        limits[metric] = status

    return UsageStatusResponse(plan=workspace.plan, limits=limits)


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload") from None
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature") from None

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        workspace_id = int(session_obj["metadata"]["workspace_id"])
        subscription_id = session_obj.get("subscription")
        customer_id = session_obj.get("customer")

        async with get_session() as db_session:
            result = await db_session.execute(
                select(Workspace).where(Workspace.id == workspace_id)
            )
            ws = result.scalar_one_or_none()
            if ws:
                ws.stripe_subscription_id = subscription_id
                ws.stripe_customer_id = customer_id
                await db_session.commit()

    elif event["type"] == "customer.subscription.updated":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")

    return {"received": True}
