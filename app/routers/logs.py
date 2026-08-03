from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.deployment import Deployment
from app.models.deployment_log import DeploymentLog
from app.schemas.log import LogCreate, LogResponse
from app.services.deployment_service import DeploymentService
from app.auth.dependencies import get_current_active_user

router = APIRouter(tags=["Deployment Logs"])


@router.get("/deployments/{id}/logs", response_model=list[LogResponse])
def get_deployment_logs(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve build and runtime logs for a specific deployment."""
    logs = DeploymentService.get_deployment_logs(db, id, current_user.id)
    return [LogResponse.model_validate(log) for log in logs]


@router.post("/deployments/{id}/logs", response_model=LogResponse, status_code=status.HTTP_201_CREATED)
def add_deployment_log(
    id: int,
    log_in: LogCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Append a log entry for a deployment."""
    dep = db.query(Deployment).filter(Deployment.id == id, Deployment.user_id == current_user.id).first()
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {id} not found"
        )

    log_entry = DeploymentLog(
        deployment_id=dep.id,
        log_level=log_in.log_level,
        message=log_in.message
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return LogResponse.model_validate(log_entry)
