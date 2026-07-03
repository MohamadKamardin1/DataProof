"""Routes for chart generation — GET charts from analysis results."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.charting import ChartBuilder
from api.database import get_session
from api.dependencies import get_current_workspace_id
from api.logging import logger
from api.models.analysis import ProxyResult
from api.models.analysis_tables import AnalysisResult
from api.models.charting import ChartSpec, ChartsResponse
from api.models.tables import Dataset, Project
from api.packs import get_pack

router = APIRouter(prefix="")


@router.get(
    "/datasets/{dataset_id}/charts",
    response_model=ChartsResponse,
)
async def get_charts(
    dataset_id: int,
    pack_id: str = "paleoclimate_xrf",
    version: int | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(get_current_user),
) -> ChartsResponse:
    """Return Plotly JSON charts for a dataset's analysis results."""
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

    if version is None:
        version_result = await session.execute(
            select(func.max(AnalysisResult.version))
            .where(
                AnalysisResult.dataset_id == dataset_id,
                AnalysisResult.pack_id == pack_id,
            )
        )
        version = version_result.scalar()
        if version is None:
            raise HTTPException(
                status_code=400,
                detail="No analysis results. Run /analyze first.",
            )

    rows_result = await session.execute(
        select(AnalysisResult)
        .where(
            AnalysisResult.dataset_id == dataset_id,
            AnalysisResult.pack_id == pack_id,
            AnalysisResult.version == version,
        )
    )
    rows = rows_result.scalars().all()
    if not rows:
        raise HTTPException(status_code=400, detail="No analysis results for this pack+version")

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

    charts_data = ChartBuilder.build_all(pack, proxy_results)

    logger.info(
        "charts_generated",
        dataset_id=dataset_id,
        pack=pack_id,
        count=len(charts_data),
    )

    chart_specs = [
        ChartSpec(
            figure_json=c["figure_json"],
            title=c["title"],
            chart_type=c["chart_type"],
        )
        for c in charts_data
    ]

    return ChartsResponse(
        pack_id=pack.id,
        pack_name=pack.name,
        charts=chart_specs,
    )
