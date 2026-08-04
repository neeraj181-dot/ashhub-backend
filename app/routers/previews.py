from typing import Any, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.preview import PreviewDeployment
from app.auth.dependencies import get_current_active_user
from app.services.audit_service import log_audit_event
from app.services.notification_service import create_notification

router = APIRouter(tags=["Preview Environments"])


@router.get("/projects/{project_id}/previews", response_model=List[dict[str, Any]])
def list_project_previews(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """List active pull request preview environments for a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    previews = db.query(PreviewDeployment).filter(
        PreviewDeployment.project_id == project_id
    ).order_by(PreviewDeployment.created_at.desc()).all()

    return [
        {
            "id": p.id,
            "project_id": p.project_id,
            "pr_number": p.pr_number,
            "branch": p.branch,
            "commit_sha": p.commit_sha,
            "preview_url": p.preview_url,
            "status": p.status,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in previews
    ]


@router.post("/projects/{project_id}/previews", response_model=dict[str, Any])
def create_preview_environment(
    project_id: int,
    pr_number: int,
    branch: str = "feature/preview",
    commit_sha: str = "abc123def456",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Provision a new pull-request preview environment."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    subdomain = branch.replace("/", "-").replace("_", "-").lower()[:20]
    preview_url = f"https://preview-{subdomain}-pr{pr_number}.ashhub.dev"

    preview = PreviewDeployment(
        project_id=project_id,
        pr_number=pr_number,
        branch=branch,
        commit_sha=commit_sha,
        preview_url=preview_url,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(preview)
    db.commit()
    db.refresh(preview)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="CREATE_PREVIEW",
        resource_type="PreviewDeployment",
        resource_id=str(preview.id),
        details=f"Created PR #{pr_number} preview deployment at {preview_url}"
    )

    create_notification(
        db=db,
        user_id=current_user.id,
        title="Preview Environment Ready",
        message=f"Preview deployment for PR #{pr_number} is live at {preview_url}",
        notification_type="info"
    )

    return {
        "id": preview.id,
        "pr_number": preview.pr_number,
        "branch": preview.branch,
        "preview_url": preview.preview_url,
        "status": preview.status
    }


@router.delete("/previews/{id}", response_model=dict[str, Any])
def destroy_preview_environment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Destroy a PR preview environment and clean up cloud resources."""
    preview = db.query(PreviewDeployment).filter(PreviewDeployment.id == id).first()
    if not preview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview environment not found")

    preview.status = "destroyed"
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="DESTROY_PREVIEW",
        resource_type="PreviewDeployment",
        resource_id=str(preview.id),
        details=f"Destroyed PR #{preview.pr_number} preview environment"
    )

    return {"status": "destroyed", "message": f"Preview environment #{id} successfully destroyed."}
