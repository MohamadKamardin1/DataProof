import io
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import get_current_user
from api.database import get_session
from api.dependencies import (
    enforce_plan_limit,
    get_current_workspace_id,
)
from api.logging import logger
from api.models.auth import User
from api.models.dataset import (
    ColumnMapping,
    ConfirmMappingRequest,
    ConfirmMappingResponse,
    DatasetDetailResponse,
    DatasetSummary,
    UploadResponse,
)
from api.models.tables import Dataset, Measurement, Project, Sample
from api.s3 import download_file_from_minio, upload_file_to_minio
from api.sniffer import HeaderSniffer, clean_numeric_value

router = APIRouter(prefix="/datasets")


async def _parse_file(file: UploadFile) -> tuple[pd.DataFrame, bytes]:
    content = await file.read()
    if file.filename is None or not file.filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported")

    if file.filename.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), comment="#")
    else:
        df = pd.read_excel(io.BytesIO(content))
    return df, content


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(lambda x: clean_numeric_value(x) if pd.notna(x) else x)
    return df


@router.get("", response_model=list[DatasetSummary])
async def list_datasets(
    session: AsyncSession = Depends(get_session),
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(get_current_user),
) -> list[DatasetSummary]:
    result = await session.execute(
        select(Dataset, Project.name.label("project_name"))
        .join(Project, Dataset.project_id == Project.id)
        .where(Project.workspace_id == workspace_id)
        .order_by(Dataset.created_at.desc())
    )
    return [
        DatasetSummary(
            dataset_id=row.Dataset.id,
            name=row.Dataset.name,
            status=row.Dataset.status,
            project_name=row.project_name,
            created_at=row.Dataset.created_at,
        )
        for row in result.all()
    ]


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(enforce_plan_limit("uploads")),
    user: User = Depends(get_current_user),
) -> UploadResponse:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        df, content = await _parse_file(file)
    except Exception as e:
        logger.error("file_parse_error", error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}") from e

    if len(df.columns) == 0:
        raise HTTPException(status_code=400, detail="File has no columns")

    schema_guess = HeaderSniffer.sniff(df)
    detected_schema = [
        ColumnMapping(
            name=g.name,
            role=g.role,
            confidence=g.confidence,
            unit=g.unit,
            data_type=g.data_type,
        )
        for g in schema_guess.columns
    ]

    # Store file in local storage or MinIO
    s3_key = upload_file_to_minio(user.id, 0, file.filename, content)

    # Create project scoped to workspace
    project = Project(name=file.filename, workspace_id=workspace_id, user_id=user.id)
    session.add(project)
    await session.flush()

    # Store in DB
    dataset = Dataset(
        name=file.filename,
        project_id=project.id,
        s3_key=s3_key,
        status="uploaded",
    )
    session.add(dataset)
    await session.flush()

    s3_key = upload_file_to_minio(user.id, dataset.id, file.filename, content)
    dataset.s3_key = s3_key
    await session.commit()

    logger.info("dataset_uploaded", dataset_id=dataset.id, name=file.filename)

    return UploadResponse(
        dataset_id=dataset.id,
        name=file.filename,
        status="uploaded",
        detected_schema=detected_schema,
        s3_key=s3_key,
    )


@router.post("/{dataset_id}/confirm-mapping", response_model=ConfirmMappingResponse)
async def confirm_mapping(
    dataset_id: int,
    request: ConfirmMappingRequest,
    session: AsyncSession = Depends(get_session),
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(get_current_user),
) -> ConfirmMappingResponse:
    result = await session.execute(
        select(Dataset)
        .join(Project, Dataset.project_id == Project.id)
        .where(Dataset.id == dataset_id, Project.workspace_id == workspace_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.status != "uploaded":
        raise HTTPException(status_code=409, detail="Dataset mapping already confirmed")

    content = download_file_from_minio(dataset.s3_key)
    filename = dataset.name.lower()
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), comment="#")
    else:
        df = pd.read_excel(io.BytesIO(content))

    # Find sample_id column
    sample_id_col = None
    for mapping in request.mappings:
        if mapping.role == "sample_id":
            sample_id_col = mapping.name
            break

    if sample_id_col is None:
        raise HTTPException(status_code=400, detail="No sample_id column selected")

    if sample_id_col not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Sample ID column '{sample_id_col}' not found in data",
        )

    samples_stored = 0
    measurements_stored = 0

    for _, row in df.iterrows():
        sample_id = str(row[sample_id_col])
        sample = Sample(sample_id=sample_id, dataset_id=dataset.id)
        session.add(sample)
        await session.flush()
        samples_stored += 1

        for mapping in request.mappings:
            if mapping.role == "measurement" and mapping.name in df.columns:
                raw_value = row[mapping.name]
                value = clean_numeric_value(raw_value)
                if value is not None:
                    measurement = Measurement(
                        sample_id=sample.id,
                        dataset_id=dataset.id,
                        column_name=mapping.name,
                        value=value,
                        unit=mapping.unit,
                    )
                    session.add(measurement)
                    measurements_stored += 1

    dataset.status = "mapped"
    await session.commit()

    logger.info(
        "dataset_mapped",
        dataset_id=dataset.id,
        samples=samples_stored,
        measurements=measurements_stored,
    )

    return ConfirmMappingResponse(
        dataset_id=dataset.id,
        status="mapped",
        samples_stored=samples_stored,
        measurements_stored=measurements_stored,
    )


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset(
    dataset_id: int,
    session: AsyncSession = Depends(get_session),
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(get_current_user),
) -> DatasetDetailResponse:
    result = await session.execute(
        select(Dataset)
        .join(Project, Dataset.project_id == Project.id)
        .where(Dataset.id == dataset_id, Project.workspace_id == workspace_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get samples with measurements eagerly loaded
    samples_result = await session.execute(
        select(Sample)
        .options(selectinload(Sample.measurements))
        .where(Sample.dataset_id == dataset_id)
    )
    samples = samples_result.scalars().all()

    # Get all measurement column names
    columns = {"sample_id": str}
    for sample in samples:
        for measurement in sample.measurements:
            if measurement.column_name not in columns:
                columns[measurement.column_name] = float | None

    # Build rows
    rows: list[dict[str, Any]] = []
    for sample in samples:
        row: dict[str, Any] = {"sample_id": sample.sample_id}
        for measurement in sample.measurements:
            row[measurement.column_name] = measurement.value
        for col_name in columns:
            if col_name not in row and col_name != "sample_id":
                row[col_name] = None
        rows.append(row)

    return DatasetDetailResponse(
        dataset_id=dataset.id,
        name=dataset.name,
        status=dataset.status,
        columns=list(columns.keys()),
        rows=rows,
    )
