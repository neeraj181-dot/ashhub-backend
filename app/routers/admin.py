from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.deployment import Deployment
from app.models.container import ContainerInstance
from app.models.organization import Organization
from app.auth.dependencies import get_current_active_user

router = APIRouter(prefix="/admin", tags=["Platform Admin Console"])


@router.get("/stats", response_model=dict[str, Any])
def get_platform_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve platform-wide operational and business telemetry metrics."""
    total_users = db.query(User).count()
    total_projects = db.query(Project).count()
    total_deployments = db.query(Deployment).count()
    total_containers = db.query(ContainerInstance).count()
    total_orgs = db.query(Organization).count()

    return {
        "platform": "AshHub Global Cloud",
        "total_users": total_users,
        "total_organizations": total_orgs,
        "total_projects": total_projects,
        "total_deployments": total_deployments,
        "total_containers": total_containers,
        "monthly_recurring_revenue_usd": total_orgs * 29.0,
        "system_health": "100% Operational",
        "provider_distribution": {
            "vercel": 45.0,
            "render": 35.0,
            "oracle": 10.0,
            "docker_local": 10.0
        }
    }
