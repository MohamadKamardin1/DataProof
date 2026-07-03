from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class InterpretationResult(Base):
    __tablename__ = "interpretation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id"), nullable=False, index=True
    )
    pack_id: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    per_sample_json: Mapped[str] = mapped_column(Text, nullable=False)
    overall_narrative: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
