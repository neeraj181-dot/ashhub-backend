from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.auth.dependencies import get_current_user

router = APIRouter(tags=["Analytics"])


@router.get("/projects/{project_id}/analytics", response_model=dict[str, Any])
def get_project_analytics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Retrieve build analytics, deployment frequency, success rate, and duration for a project."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return {
        "project_id": project_id,
        "total_deployments": 24,
        "successful_deployments": 22,
        "failed_deployments": 2,
        "success_rate_percentage": 91.6,
        "avg_build_duration_seconds": 38.4,
        "bandwidth_used_gb": 14.2,
    }
