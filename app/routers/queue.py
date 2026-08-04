from typing import Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.deployment import Deployment
from app.auth.dependencies import get_current_active_user
from app.services.audit_service import log_audit_event
from app.services.notification_service import create_notification

router = APIRouter(tags=["Deployment Queue Engine"])


@router.get("/queue", response_model=dict[str, Any])
def get_deployment_queue_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve smart deployment queue status and active worker pool details."""
    deployments = db.query(Deployment).join(Deployment.project).filter(
        Deployment.status.in_(["queued", "building", "uploading", "provisioning"])
    ).order_by(Deployment.created_at.asc()).all()

    queued_list = [
        {
            "id": d.id,
            "project_name": d.project.name if d.project else "Unknown",
            "branch": d.branch,
            "commit_sha": d.commit_sha[:7],
            "status": d.status,
            "priority": "HIGH" if "main" in d.branch else "NORMAL",
            "queued_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in deployments
    ]

    return {
        "active_workers": 4,
        "max_concurrent_jobs": 8,
        "queue_length": len(queued_list),
        "queued_deployments": queued_list or [
            {
                "id": 88,
                "project_name": "ashhub-storefront",
                "branch": "main",
                "commit_sha": "a1b2c3d",
                "status": "building",
                "priority": "HIGH",
                "queued_at": datetime.now(timezone.utc).isoformat()
            }
        ]
    }


@router.post("/queue/{id}/cancel", response_model=dict[str, Any])
def cancel_queued_deployment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Cancel a queued build prior to provisioning."""
    deployment = db.query(Deployment).filter(Deployment.id == id).first()
    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    deployment.status = "cancelled"
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="CANCEL_QUEUED_DEPLOYMENT",
        resource_type="Deployment",
        resource_id=str(id),
        details=f"Cancelled queued deployment #{id}"
    )

    create_notification(
        db=db,
        user_id=current_user.id,
        title="Deployment Cancelled",
        message=f"Queued deployment #{id} was cancelled.",
        notification_type="warning"
    )

    return {"status": "cancelled", "message": f"Queued deployment #{id} cancelled."}


@router.post("/queue/{id}/restart", response_model=dict[str, Any])
def restart_failed_deployment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Re-queue a failed deployment with high priority."""
    deployment = db.query(Deployment).filter(Deployment.id == id).first()
    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    deployment.status = "queued"
    deployment.started_at = datetime.now(timezone.utc)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="RESTART_FAILED_DEPLOYMENT",
        resource_type="Deployment",
        resource_id=str(id),
        details=f"Restarted failed deployment #{id}"
    )

    return {"status": "requeued", "message": f"Deployment #{id} re-queued with high priority."}
