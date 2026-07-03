"""Routes for LLM interpretation of analysis results (async Celery jobs)."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.celery_app import celery_app
from api.database import get_session
from api.dependencies import enforce_plan_limit, get_current_workspace_id
from api.logging import logger
from api.models.analysis import ProxyResult
from api.models.analysis_tables import AnalysisResult
from api.models.auth import User
from api.models.interpretation import (
    InterpretationJobResponse,
    InterpretationResultResponse,
    InterpretationStartResponse,
    VerifiedCitation,
)
from api.models.tables import Dataset, Project
from api.packs import get_pack
from api.tasks import interpret_dataset_task

router = APIRouter(prefix="")


@router.post(
    "/datasets/{dataset_id}/interpret",
    response_model=InterpretationStartResponse,
    status_code=202,
)
async def start_interpretation(
    dataset_id: int,
    pack_id: str = "paleoclimate_xrf",
    session: AsyncSession = Depends(get_session),  # noqa: B008
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(enforce_plan_limit("reports_generated")),
    user: User = Depends(get_current_user),
) -> InterpretationStartResponse:
    """Start an async interpretation job. Returns a job_id for status polling."""
    # Verify dataset exists and is scoped to workspace
    result = await session.execute(
        select(Dataset)
        .join(Project, Dataset.project_id == Project.id)
        .where(Dataset.id == dataset_id, Project.workspace_id == workspace_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Verify pack exists
    pack = get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Analysis pack {pack_id!r} not found")

    # Get the latest analysis version
    version_result = await session.execute(
        select(func.max(AnalysisResult.version))
        .where(
            AnalysisResult.dataset_id == dataset_id,
            AnalysisResult.pack_id == pack_id,
        )
    )
    analysis_version = version_result.scalar()
    if analysis_version is None:
        raise HTTPException(
            status_code=400,
            detail="No analysis results found. Run /analyze first.",
        )

    # Fetch the latest analysis results
    results_result = await session.execute(
        select(AnalysisResult)
        .where(
            AnalysisResult.dataset_id == dataset_id,
            AnalysisResult.pack_id == pack_id,
            AnalysisResult.version == analysis_version,
        )
    )
    rows = results_result.scalars().all()
    if not rows:
        raise HTTPException(status_code=400, detail="No analysis results found for this pack")

    proxy_results = [
        ProxyResult(
            proxy_id=r.proxy_id,
            label=r.proxy_label,
            sample_id=r.sample_id,
            value=r.value,
            unit=r.unit,
        )
        for r in rows
    ]

    results_json = json.dumps([r.model_dump() for r in proxy_results])

    # Dispatch Celery task
    task = interpret_dataset_task.delay(
        dataset_id=dataset_id,
        pack_id=pack_id,
        analysis_version=analysis_version,
        results_data=results_json,
    )

    logger.info(
        "interpretation_dispatched",
        dataset_id=dataset_id,
        pack=pack_id,
        job_id=task.id,
        samples=len({r.sample_id for r in proxy_results}),
    )

    return InterpretationStartResponse(
        job_id=task.id,
        status_url=f"/api/v1/jobs/{task.id}",
    )


@router.get("/jobs/{job_id}", response_model=InterpretationJobResponse)
async def get_job_status(
    job_id: str,
    _=Depends(get_current_user),
) -> InterpretationJobResponse:
    """Poll job status. Returns pending/running/completed/failed with result on completion."""
    async_result = celery_app.AsyncResult(job_id)

    status_map = {
        "PENDING": "pending",
        "RECEIVED": "running",
        "STARTED": "running",
        "RETRY": "running",
        "PROGRESS": "running",
        "SUCCESS": "completed",
        "FAILURE": "failed",
    }

    status = status_map.get(async_result.status, "pending")

    result_data = None
    error = None

    if status == "completed":
        try:
            task_result = async_result.result
            result_data = InterpretationResultResponse(
                per_sample=task_result["per_sample"],
                overall_narrative=task_result["overall_narrative"],
                citations=[VerifiedCitation(**c) for c in task_result["citations"]],
            )
        except Exception as e:
            logger.error("job_result_parse_error", job_id=job_id, error=str(e))
            status = "failed"
            error = f"Failed to parse result: {e}"

    elif status == "failed":
        try:
            error = str(async_result.result)
        except Exception:
            error = "Unknown error"

    return InterpretationJobResponse(
        job_id=job_id,
        status=status,
        result=result_data,
        error=error,
    )
