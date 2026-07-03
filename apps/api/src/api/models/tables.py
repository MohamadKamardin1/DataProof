from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base

if TYPE_CHECKING:
    from api.models.analysis_tables import AnalysisResult
    from api.models.auth import Workspace


def utcnow() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="projects")
    datasets: Mapped[list[Dataset]] = relationship(
        "Dataset", back_populates="project", cascade="all, delete-orphan"
    )


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    detected_schema: Mapped[str | None] = mapped_column(nullable=True)
    confirmed_mapping: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped[Project] = relationship("Project", back_populates="datasets")
    samples: Mapped[list[Sample]] = relationship(
        "Sample", back_populates="dataset", cascade="all, delete-orphan"
    )
    measurements: Mapped[list[Measurement]] = relationship(
        "Measurement", back_populates="dataset", cascade="all, delete-orphan"
    )
    analysis_results: Mapped[list[AnalysisResult]] = relationship(
        "AnalysisResult", back_populates="dataset", cascade="all, delete-orphan"
    )


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="samples")
    measurements: Mapped[list[Measurement]] = relationship(
        "Measurement",
        back_populates="sample",
        cascade="all, delete-orphan",
        foreign_keys="Measurement.sample_id",
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey("samples.id"), nullable=False)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    column_name: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[float] = mapped_column(Double, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sample: Mapped[Sample] = relationship(
        "Sample", back_populates="measurements", foreign_keys=[sample_id]
    )
    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="measurements")
