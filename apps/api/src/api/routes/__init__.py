from api.routes.analysis import router as analysis_router
from api.routes.auth import router as auth_router
from api.routes.billing import router as billing_router
from api.routes.charts import router as charts_router
from api.routes.datasets import router as datasets_router
from api.routes.health import router as health_router
from api.routes.interpretation import router as interpretation_router
from api.routes.reports import router as reports_router
from api.routes.workspaces import router as workspaces_router

__all__ = [
    "analysis_router",
    "auth_router",
    "billing_router",
    "charts_router",
    "datasets_router",
    "health_router",
    "interpretation_router",
    "reports_router",
    "workspaces_router",
]
