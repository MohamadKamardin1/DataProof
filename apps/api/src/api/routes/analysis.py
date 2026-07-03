"""Routes for analysis pack listing and calculation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.database import get_session
from api.dependencies import (
    enforce_plan_limit,
    get_current_workspace_id,
)
from api.formula import DivisionByZeroError, MissingVariableError, eval_formula
from api.logging import logger
from api.models.analysis import AnalysisResponse, PackSummary, ProxyResult
from api.models.analysis_tables import AnalysisResult
from api.models.auth import User
from api.models.tables import Dataset, Measurement, Project, Sample
from api.packs import get_all_packs, get_compatible_packs, get_pack, normalize_column_name

router = APIRouter(prefix="")


@router.get("/packs", response_model=list[PackSummary])
async def list_packs() -> list[PackSummary]:
    packs = get_all_packs()
    return [
        PackSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            required_columns=p.required_columns,
        )
        for p in packs
    ]


@router.get("/datasets/{dataset_id}/compatible-packs", response_model=list[PackSummary])
async def compatible_packs(
    dataset_id: int,
    session: AsyncSession = Depends(get_session),
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(get_current_user),
) -> list[PackSummary]:
    result = await session.execute(
        select(Dataset)
        .join(Project, Dataset.project_id == Project.id)
        .where(Dataset.id == dataset_id, Project.workspace_id == workspace_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    meas_result = await session.execute(
        select(Measurement.column_name)
        .where(Measurement.dataset_id == dataset_id)
        .distinct()
    )
    column_names = {row[0] for row in meas_result.all()}

    compatible = get_compatible_packs(column_names)
    return [
        PackSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            required_columns=p.required_columns,
        )
        for p in compatible
    ]


@router.post("/datasets/{dataset_id}/analyze", response_model=AnalysisResponse)
async def analyze_dataset(
    dataset_id: int,
    pack_id: str = "paleoclimate_xrf",
    session: AsyncSession = Depends(get_session),
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(enforce_plan_limit("analyses_run")),
    user: User = Depends(get_current_user),
) -> AnalysisResponse:
    result = await session.execute(
        select(Dataset)
        .join(Project, Dataset.project_id == Project.id)
        .where(Dataset.id == dataset_id, Project.workspace_id == workspace_id)
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    pack = get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Analysis pack {pack_id!r} not found")

    # Fetch all measurements for this dataset
    meas_result = await session.execute(
        select(Measurement, Sample)
        .join(Sample, Measurement.sample_id == Sample.id)
        .where(Measurement.dataset_id == dataset_id)
    )
    rows = meas_result.all()
    if not rows:
        raise HTTPException(status_code=400, detail="Dataset has no measurements")

    # Build lookup: sample_external_id -> {normalized_column_name -> value}
    sample_values: dict[str, dict[str, float]] = {}
    sample_id_map: dict[str, str] = {}  # external sample_id -> external sample_id (identity)
    for measurement, sample in rows:
        sid = sample.sample_id
        if sid not in sample_values:
            sample_values[sid] = {}
            sample_id_map[sid] = sid
        col_key = normalize_column_name(measurement.column_name)
        sample_values[sid][col_key] = measurement.value

    # Determine version number
    version_result = await session.execute(
        select(func.coalesce(func.max(AnalysisResult.version), 0))
        .where(
            AnalysisResult.dataset_id == dataset_id,
            AnalysisResult.pack_id == pack_id,
        )
    )
    version = (version_result.scalar() or 0) + 1

    # Compute proxies for each sample
    proxy_results: list[ProxyResult] = []
    for sid, values in sample_values.items():
        for proxy in pack.proxies:
            try:
                computed = eval_formula(proxy.formula, values)
            except MissingVariableError:
                logger.warning(
                    "missing_variable",
                    proxy_id=proxy.id,
                    sample_id=sid,
                    formula=proxy.formula,
                )
                computed = None
            except DivisionByZeroError:
                logger.warning(
                    "division_by_zero",
                    proxy_id=proxy.id,
                    sample_id=sid,
                    formula=proxy.formula,
                )
                computed = None

            ar = AnalysisResult(
                dataset_id=dataset_id,
                pack_id=pack_id,
                version=version,
                proxy_id=proxy.id,
                proxy_label=proxy.label,
                sample_id=sid,
                value=computed,
                unit=proxy.unit,
            )
            session.add(ar)
            proxy_results.append(
                ProxyResult(
                    proxy_id=proxy.id,
                    label=proxy.label,
                    sample_id=sid,
                    value=computed,
                    unit=proxy.unit,
                )
            )

    await session.commit()

    logger.info(
        "analysis_computed",
        dataset_id=dataset_id,
        pack_id=pack_id,
        version=version,
        samples=len(sample_values),
        proxies=len(pack.proxies),
    )

    return AnalysisResponse(
        dataset_id=dataset_id,
        pack=pack_id,
        version=version,
        results=proxy_results,
    )
