from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
# Import all models to ensure they are registered with SQLAlchemy Base metadata
import app.models  # noqa: F401
from app.routers import (
    auth_router,
    github_router,
    projects_router,
    deployments_router,
    providers_router,
    logs_router,
    health_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB tables exist
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown logic (if needed)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AshHub Open-Source Deployment Platform Backend API",
    version=settings.VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(github_router)
app.include_router(projects_router)
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
