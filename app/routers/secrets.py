from typing import Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.secret import SecretVault
from app.auth.dependencies import get_current_active_user
from app.utils.encryption import encrypt_env_vars, decrypt_env_vars
from app.services.audit_service import log_audit_event

router = APIRouter(tags=["Secrets Manager"])


@router.get("/projects/{project_id}/secrets", response_model=List[dict[str, Any]])
def list_project_secrets(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve masked encrypted secrets for a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    secrets = db.query(SecretVault).filter(SecretVault.project_id == project_id).all()

    if not secrets and project.env_vars:
        # Auto-migrate project env_vars to SecretVault
        for k, v in project.env_vars.items():
            enc_str = encrypt_env_vars({k: v})
            sec = SecretVault(
                project_id=project_id,
                key=k,
                encrypted_value=enc_str,
                version=1
            )
            db.add(sec)
        db.commit()
        secrets = db.query(SecretVault).filter(SecretVault.project_id == project_id).all()

    return [
        {
            "id": s.id,
            "project_id": s.project_id,
            "key": s.key,
            "masked_value": "••••••••••••••••",
            "version": s.version,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        for s in secrets
    ]


@router.post("/projects/{project_id}/secrets", response_model=dict[str, Any])
def create_or_rotate_secret(
    project_id: int,
    key: str,
    value: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Create or rotate an encrypted secret in the vault."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    existing = db.query(SecretVault).filter(SecretVault.project_id == project_id, SecretVault.key == key).first()

    enc_val = encrypt_env_vars({key: value})

    if existing:
        existing.encrypted_value = enc_val
        existing.version += 1
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        sec = existing
        action = "ROTATE_SECRET"
    else:
        sec = SecretVault(
            project_id=project_id,
            key=key,
            encrypted_value=enc_val,
            version=1
        )
        db.add(sec)
        db.commit()
        db.refresh(sec)
        action = "CREATE_SECRET"

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action=action,
        resource_type="SecretVault",
        resource_id=str(sec.id),
        details=f"{action} for key '{key}' (v{sec.version})"
    )

    return {
        "id": sec.id,
        "key": sec.key,
        "masked_value": "••••••••••••••••",
        "version": sec.version,
        "updated_at": sec.updated_at.isoformat()
    }


@router.delete("/secrets/{id}", response_model=dict[str, Any])
def delete_secret(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Delete a secret entry from vault."""
    sec = db.query(SecretVault).filter(SecretVault.id == id).first()
    if not sec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

    db.delete(sec)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="DELETE_SECRET",
        resource_type="SecretVault",
        resource_id=str(id),
        details=f"Deleted secret key '{sec.key}'"
    )

    return {"status": "deleted", "message": f"Secret #{id} deleted."}
