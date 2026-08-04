from typing import Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.deployment import Deployment
from app.models.organization import Organization

PLAN_QUOTAS = {
    "free": {
        "max_projects": 3,
        "max_deployments_per_month": 50,
        "max_members": 2,
        "max_bandwidth_gb": 10.0,
        "max_container_hours": 100
    },
    "pro": {
        "max_projects": 15,
        "max_deployments_per_month": 500,
        "max_members": 10,
        "max_bandwidth_gb": 100.0,
        "max_container_hours": 1000
    },
    "team": {
        "max_projects": 50,
        "max_deployments_per_month": 2500,
        "max_members": 30,
        "max_bandwidth_gb": 500.0,
        "max_container_hours": 5000
    },
    "enterprise": {
        "max_projects": 9999,
        "max_deployments_per_month": 999999,
        "max_members": 9999,
        "max_bandwidth_gb": 10000.0,
        "max_container_hours": 999999
    }
}


class QuotaService:
    """Service verifying plan resource limits and usage quotas."""

    @staticmethod
    def enforce_project_quota(db: Session, user_id: int, org_id: int | None = None) -> None:
        plan = "free"
        if org_id:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if org:
                plan = org.plan.lower()

        limits = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])
        count = db.query(Project).filter(Project.user_id == user_id).count()

        if count >= limits["max_projects"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Plan project limit reached ({limits['max_projects']} max for {plan.upper()} plan). Upgrade your plan to create more projects."
            )
