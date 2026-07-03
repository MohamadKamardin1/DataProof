"""DataProof API — main FastAPI application."""

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import __version__
from api.config import settings
from api.logging import logger
from api.routes import (
    analysis_router,
    auth_router,
    billing_router,
    charts_router,
    datasets_router,
    health_router,
    interpretation_router,
    reports_router,
    workspaces_router,
)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.25,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("api_startup", version=__version__, environment=settings.environment)
    yield
    logger.info("api_shutdown")


app = FastAPI(
    title="DataProof API",
    description="Scientific data analysis and interpretation",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "https://data.mohamadkamardin.space",
        "https://dataproofserver.mohamadkamardin.space",
        "https://dataproofserver.mohamadkamardin.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse({"message": "DataProof API", "version": __version__})


# Public routes (no auth)
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")

# Protected routes (auth required — enforced via per-route dependencies)
app.include_router(workspaces_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(interpretation_router, prefix="/api/v1")
app.include_router(charts_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
