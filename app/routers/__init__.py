from app.routers.auth import router as auth_router
from app.routers.github import router as github_router
from app.routers.projects import router as projects_router
from app.routers.deployments import router as deployments_router
from app.routers.providers import router as providers_router
from app.routers.logs import router as logs_router
from app.routers.health import router as health_router
from app.routers.audit import router as audit_router
from app.routers.system_status import router as system_status_router
from app.routers.analytics import router as analytics_router
from app.routers.search import router as search_router
from app.routers.notifications import router as notifications_router
from app.routers.webhooks import router as webhooks_router
from app.routers.templates import router as templates_router
from app.routers.activity import router as activity_router
from app.routers.previews import router as previews_router
from app.routers.releases import router as releases_router
from app.routers.cache import router as cache_router
from app.routers.queue import router as queue_router
from app.routers.containers import router as containers_router
from app.routers.secrets import router as secrets_router
from app.routers.registry import router as registry_router
from app.routers.organizations import router as organizations_router
from app.routers.api_keys import router as api_keys_router
from app.routers.billing import router as billing_router
from app.routers.admin import router as admin_router
from app.routers.ai import router as ai_router

__all__ = [
    "auth_router",
    "github_router",
    "projects_router",
    "deployments_router",
    "providers_router",
    "logs_router",
    "health_router",
    "audit_router",
    "system_status_router",
    "analytics_router",
    "search_router",
    "notifications_router",
    "webhooks_router",
    "templates_router",
    "activity_router",
    "previews_router",
    "releases_router",
    "cache_router",
    "queue_router",
    "containers_router",
    "secrets_router",
    "registry_router",
    "organizations_router",
    "api_keys_router",
    "billing_router",
    "admin_router",
    "ai_router",
]
