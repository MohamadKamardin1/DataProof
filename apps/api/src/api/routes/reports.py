"""Routes for report assembly and export."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.database import get_session
from api.deepseek import generate_report_narrative
from api.dependencies import enforce_plan_limit, get_current_workspace_id
from api.logging import logger
from api.models.analysis_tables import AnalysisResult
from api.models.auth import User
from api.models.interpretation_tables import InterpretationResult
from api.models.report import ReportResponse
from api.models.report_tables import Report
from api.models.tables import Dataset, Project
from api.packs import get_pack
from api.reports import ReportAssembler

router = APIRouter(prefix="")


@router.post(
    "/datasets/{dataset_id}/report",
    response_model=ReportResponse,
    status_code=201,
)
async def create_report(
    dataset_id: int,
    pack_id: str = "paleoclimate_xrf",
    session: AsyncSession = Depends(get_session),  # noqa: B008
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(enforce_plan_limit("reports_generated")),
    user: User = Depends(get_current_user),
) -> ReportResponse:
    """Create a report record for a dataset. Does NOT export — just creates the draft."""
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
        raise HTTPException(status_code=404, detail=f"Pack {pack_id!r} not found")

    report = Report(
        dataset_id=dataset_id,
        pack_id=pack_id,
        status="draft",
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    logger.info("report_created", report_id=report.id, dataset_id=dataset_id, pack=pack_id)

    return ReportResponse(
        report_id=report.id,
        dataset_id=report.dataset_id,
        pack_id=report.pack_id,
        status=report.status,
        created_at=report.created_at,
    )


@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: int,
    format: str = "pdf",
    session: AsyncSession = Depends(get_session),  # noqa: B008
    workspace_id: int = Depends(get_current_workspace_id),
    _=Depends(enforce_plan_limit("reports_generated")),
    user: User = Depends(get_current_user),
):
    """Export a report as PDF or DOCX.

    Free-tier reports get watermarked output.
    """
    result = await session.execute(
        select(Report)
        .join(Dataset, Report.dataset_id == Dataset.id)
        .join(Project, Dataset.project_id == Project.id)
        .where(Report.id == report_id, Project.workspace_id == workspace_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    pack = get_pack(report.pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Pack {report.pack_id!r} not found")

    # Fetch latest analysis results
    rows_result = await session.execute(
        select(AnalysisResult)
        .where(
            AnalysisResult.dataset_id == report.dataset_id,
            AnalysisResult.pack_id == report.pack_id,
        )
        .order_by(AnalysisResult.version.desc())
    )
    analysis_rows = rows_result.scalars().all()
    if not analysis_rows:
        raise HTTPException(status_code=400, detail="No analysis results found")

    # Fetch latest interpretation if available
    interp_result = await session.execute(
        select(InterpretationResult)
        .where(
            InterpretationResult.dataset_id == report.dataset_id,
            InterpretationResult.pack_id == report.pack_id,
        )
        .order_by(InterpretationResult.created_at.desc())
    )
    interpretation = interp_result.scalar()

    # Determine tier from workspace plan
    from api.models.auth import Workspace as WsModel
    ws_result = await session.execute(select(WsModel).where(WsModel.id == workspace_id))
    ws = ws_result.scalar_one_or_none()
    user_tier = ws.plan if ws else "free"

    # Build proxy stats for DeepSeek
    proxy_results_for_deepseek = []
    proxy_ids = sorted({r.proxy_id for r in analysis_rows})
    for pid in proxy_ids:
        values = [r.value for r in analysis_rows if r.proxy_id == pid and r.value is not None]
        label = next((p.label for p in pack.proxies if p.id == pid), pid)
        formula = next((p.formula for p in pack.proxies if p.id == pid), "")
        if values:
            proxy_results_for_deepseek.append({
                "label": label,
                "formula": formula,
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            })

    # Generate DeepSeek narrative
    deepseek_data = await generate_report_narrative(
        pack_name=pack.name,
        pack_description=pack.description or "",
        proxy_results=proxy_results_for_deepseek,
        sample_count=len({r.sample_id for r in analysis_rows}),
    )

    if format == "docx":
        docx_bytes = ReportAssembler.assemble_docx(
            pack, list(analysis_rows), interpretation, user_tier, deepseek_data
        )
        filename = f"dataproof_report_{report.dataset_id}_{pack.id}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Default: PDF
    pdf_bytes = ReportAssembler.assemble_pdf(
        pack, list(analysis_rows), interpretation, user_tier, deepseek_data
    )
    filename = f"dataproof_report_{report.dataset_id}_{pack.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
