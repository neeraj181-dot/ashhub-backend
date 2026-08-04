from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.release import Release
from app.auth.dependencies import get_current_active_user
from app.services.audit_service import log_audit_event
from app.services.notification_service import create_notification

router = APIRouter(tags=["Release Management"])


@router.get("/projects/{project_id}/releases", response_model=List[dict[str, Any]])
def list_project_releases(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Fetch release version history for a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    releases = db.query(Release).filter(
        Release.project_id == project_id
    ).order_by(Release.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "deployment_id": r.deployment_id,
            "version": r.version,
            "git_tag": r.git_tag,
            "commit_sha": r.commit_sha,
            "author": r.author,
            "release_notes": r.release_notes,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in releases
    ]


@router.post("/projects/{project_id}/releases", response_model=dict[str, Any])
def create_release(
    project_id: int,
    version: str,
    git_tag: Optional[str] = None,
    commit_sha: str = "main-sha-latest",
    release_notes: Optional[str] = "Production release build",
    deployment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Publish a new tagged release version for a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    rel = Release(
        project_id=project_id,
        deployment_id=deployment_id,
        version=version,
        git_tag=git_tag or f"v{version.lstrip('v')}",
        commit_sha=commit_sha,
        author=current_user.full_name or current_user.email,
        release_notes=release_notes,
        status="published"
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="CREATE_RELEASE",
        resource_type="Release",
        resource_id=str(rel.id),
        details=f"Published release {rel.version} ({rel.git_tag})"
    )

    create_notification(
        db=db,
        user_id=current_user.id,
        title="Release Published",
        message=f"Release {rel.version} has been published to production.",
        notification_type="success"
    )

    return {
        "id": rel.id,
        "version": rel.version,
        "git_tag": rel.git_tag,
        "status": rel.status,
        "created_at": rel.created_at.isoformat()
    }
