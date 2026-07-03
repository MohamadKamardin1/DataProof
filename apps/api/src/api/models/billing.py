"""Billing and usage-metering SQLAlchemy models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="analyses_run | reports_generated | uploads"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


PLAN_LIMITS: dict[str, dict[str, int | None]] = {
    "free": {
        "uploads": 10,
        "analyses_run": 20,
        "reports_generated": 5,
        "api_rate_per_minute": 30,
    },
    "pro": {
        "uploads": None,  # unlimited
        "analyses_run": None,
        "reports_generated": None,
        "api_rate_per_minute": 300,
    },
    "lab": {
        "uploads": None,
        "analyses_run": None,
        "reports_generated": None,
        "api_rate_per_minute": 1000,
    },
}
