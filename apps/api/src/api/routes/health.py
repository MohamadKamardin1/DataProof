from datetime import UTC, datetime

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from minio import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api import __version__
from api.config import settings
from api.database import get_session
from api.logging import logger
from api.models import HealthResponse

router = APIRouter()


async def check_redis() -> bool:
    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        return True
    except Exception:
        return False


def check_minio() -> bool:
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        client.list_buckets()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    db_ok = True
    redis_ok = await check_redis()
    minio_ok = check_minio()

    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("database_check_failed", error=str(e))
        db_ok = False

    status = ("healthy" if minio_ok else "degraded") if db_ok and redis_ok else "unhealthy"

    logger.info(
        "health_check",
        status=status,
        database=db_ok,
        redis=redis_ok,
        minio=minio_ok,
    )

    return HealthResponse(
        status=status,
        version=__version__,
        timestamp=datetime.now(UTC),
        checks={
            "database": db_ok,
            "redis": redis_ok,
            "minio": minio_ok,
        },
    )
