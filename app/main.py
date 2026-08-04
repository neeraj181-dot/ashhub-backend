import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
import app.models  # noqa: F401
from app.routers import (
    auth_router,
    github_router,
    projects_router,
    deployments_router,
    providers_router,
    logs_router,
    health_router,
    audit_router,
    system_status_router,
    analytics_router,
    search_router,
    notifications_router,
    webhooks_router,
    templates_router,
    activity_router,
    previews_router,
    releases_router,
    cache_router,
    queue_router,
    containers_router,
    secrets_router,
    registry_router,
    organizations_router,
    api_keys_router,
    billing_router,
    admin_router,
    ai_router,
)

logger = logging.getLogger("ashhub.access")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB tables exist
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AshHub Open-Source Deployment Platform Backend API",
    version=settings.VERSION,
    lifespan=lifespan
)

# Configure CORS middleware BEFORE all routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Detailed backend request logger (HTTP Method, Endpoint, Status Code, Execution Time)."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


# Register API Routers
app.include_router(auth_router)
app.include_router(github_router)
app.include_router(webhooks_router)
app.include_router(templates_router)
app.include_router(activity_router)
app.include_router(audit_router)
app.include_router(system_status_router)
app.include_router(search_router)
app.include_router(notifications_router)
app.include_router(previews_router)
app.include_router(releases_router)
app.include_router(cache_router)
app.include_router(queue_router)
app.include_router(containers_router)
app.include_router(secrets_router)
app.include_router(registry_router)
app.include_router(organizations_router)
app.include_router(api_keys_router)
app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(ai_router)
app.include_router(projects_router)
app.include_router(analytics_router)
app.include_router(deployments_router)
app.include_router(providers_router)
app.include_router(logs_router)
app.include_router(health_router)


@app.get("/")
def read_root():
    """Root status endpoint for AshHub Backend API."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs_url": "/docs"
    }
