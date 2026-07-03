"""Pydantic models for reports and export."""

from datetime import datetime

from pydantic import BaseModel


class ReportCreateRequest(BaseModel):
    dataset_id: int
    pack_id: str
    interpretation_job_id: str | None = None


class ReportResponse(BaseModel):
    report_id: int
    dataset_id: int
    pack_id: str
    status: str
    created_at: datetime


class ReportExportRequest(BaseModel):
    format: str = "pdf"  # "pdf" | "docx"


class ReportExportResponse(BaseModel):
    download_url: str
