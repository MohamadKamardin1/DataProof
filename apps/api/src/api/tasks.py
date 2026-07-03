"""Celery tasks for async interpretation jobs."""
import json

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.celery_app import celery_app
from api.citations import validate_citations
from api.config import settings
from api.llm import DeepSeekEngine
from api.logging import logger
from api.models.analysis import ProxyResult
from api.models.interpretation_tables import InterpretationResult
from api.packs import get_pack


class DatabaseTask(Task):
    _engine = None
    _session_factory = None

    @property
    def session_factory(self):
        if self._session_factory is None:
            self._engine = create_async_engine(
                settings.database_url,
                pool_pre_ping=True,
                pool_size=2,
                max_overflow=4,
            )
            self._session_factory = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )
        return self._session_factory


@celery_app.task(bind=True, base=DatabaseTask, name="interpret_dataset")
def interpret_dataset_task(
    self,
    dataset_id: int,
    pack_id: str,
    analysis_version: int,
    results_data: str,  # JSON-serialized list of ProxyResult dicts
) -> dict:
    """Run interpretation: call DeepSeek, validate citations, store result."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _run_interpretation(dataset_id, pack_id, analysis_version, results_data, self)
        )
    finally:
        loop.close()


async def _run_interpretation(
    dataset_id: int,
    pack_id: str,
    analysis_version: int,
    results_data: str,
    task: Task,
) -> dict:
    """Async coroutine for the interpretation pipeline."""
    pack = get_pack(pack_id)
    if pack is None:
        raise ValueError(f"Analysis pack {pack_id!r} not found")

    results_list = json.loads(results_data)
    proxy_results = [ProxyResult(**r) for r in results_list]

    task.update_state(state="RUNNING", meta={"progress": "Calling DeepSeek API"})
    samples = len({r.sample_id for r in proxy_results})
    logger.info("interpretation_start", dataset_id=dataset_id, pack=pack_id, samples=samples)

    engine = DeepSeekEngine()
    llm_response = engine.interpret(pack, proxy_results)

    task.update_state(state="RUNNING", meta={"progress": "Validating citations"})
    logger.info("citation_validation_start", count=len(llm_response.citations))

    verified_citations = validate_citations(llm_response.citations)

    task.update_state(state="RUNNING", meta={"progress": "Storing results"})

    session_factory = DatabaseTask.session_factory
    if session_factory is None:
        raise RuntimeError("DatabaseTask session_factory is uninitialised")

    async with session_factory() as session:
        for entry in llm_response.per_sample:
            if not any(
                f"{r.proxy_id}" in entry.rationale or str(r.value or "") in entry.rationale
                for r in proxy_results
                if r.sample_id == entry.sample_id
            ):
                logger.warning(
                    "citation_value_missing_in_rationale",
                    sample_id=entry.sample_id,
                    rationale=entry.rationale[:100],
                )

        interpretation = InterpretationResult(
            dataset_id=dataset_id,
            pack_id=pack_id,
            analysis_version=analysis_version,
            per_sample_json=json.dumps([e.model_dump() for e in llm_response.per_sample]),
            overall_narrative=llm_response.overall_narrative,
            citations_json=json.dumps([c.model_dump() for c in verified_citations]),
        )
        session.add(interpretation)
        await session.commit()

    logger.info(
        "interpretation_complete",
        dataset_id=dataset_id,
        pack=pack_id,
        citations_verified=sum(1 for c in verified_citations if c.verified),
        citations_total=len(verified_citations),
    )

    return {
        "dataset_id": dataset_id,
        "pack": pack_id,
        "analysis_version": analysis_version,
        "per_sample": [e.model_dump() for e in llm_response.per_sample],
        "overall_narrative": llm_response.overall_narrative,
        "citations": [c.model_dump() for c in verified_citations],
    }
