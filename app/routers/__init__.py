from app.routers.auth import router as auth_router
from app.routers.github import router as github_router
from app.routers.projects import router as projects_router
from app.routers.deployments import router as deployments_router
from app.routers.providers import router as providers_router
from app.routers.logs import router as logs_router
from app.routers.health import router as health_router

__all__ = [
    "auth_router",
    "github_router",
    "projects_router",
    "deployments_router",
    "providers_router",
    "logs_router",
    "health_router",
]
