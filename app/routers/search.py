from typing import Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.project import Project
from app.models.deployment import Deployment
from app.models.user import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/search", tags=["Global Search"])


@router.get("", response_model=dict[str, List[Any]])
def global_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Execute global search across projects and deployments."""
    term = f"%{q}%"

    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id, Project.name.ilike(term))
        .all()
    )

    deployments = (
        db.query(Deployment)
        .filter(
            Deployment.user_id == current_user.id,
            (Deployment.commit_hash.ilike(term) | Deployment.branch.ilike(term)),
        )
        .all()
    )

    return {
        "projects": [
            {"id": p.id, "name": p.name, "description": p.description}
            for p in projects
        ],
        "deployments": [
            {
                "id": d.id,
                "project_id": d.project_id,
                "branch": d.branch,
                "commit_hash": d.commit_hash,
                "status": d.status,
            }
            for d in deployments
        ],
    }
