from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ColumnMapping(BaseModel):
    name: str
    role: Literal["sample_id", "measurement", "ignore"]
    confidence: float
    unit: str | None = None
    data_type: str | None = None


class UploadResponse(BaseModel):
    dataset_id: int
    name: str
    status: str = "uploaded"
    detected_schema: list[ColumnMapping]
    s3_key: str


class DatasetSummary(BaseModel):
    dataset_id: int
    name: str
    status: str
    project_name: str
    created_at: datetime


class ConfirmMappingRequest(BaseModel):
    mappings: list[ColumnMapping]


class ConfirmMappingResponse(BaseModel):
    dataset_id: int
    status: str = "mapped"
    samples_stored: int
    measurements_stored: int


class MeasurementRow(BaseModel):
    sample_id: str
    column_name: str
    value: float
    unit: str | None = None


class DatasetDetailResponse(BaseModel):
    dataset_id: int
    name: str
    status: str
    columns: list[str]
    rows: list[dict[str, str | float | None]]
