import secrets
import hashlib
from typing import Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.auth.dependencies import get_current_active_user
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/api-keys", tags=["Scoped API Keys"])


@router.get("", response_model=List[dict[str, Any]])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve API keys for authenticated user."""
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None
        }
        for k in keys
    ]


@router.post("", response_model=dict[str, Any])
def create_api_key(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Generate a new scoped API Key."""
    name = payload.get("name", "Default API Key")
    scopes = payload.get("scopes", "read,write,deploy")

    raw_secret = f"ash_live_{secrets.token_hex(20)}"
    prefix = raw_secret[:12] + "..."
    key_hash = hashlib.sha256(raw_secret.encode()).hexdigest()

    key_entry = APIKey(
        user_id=current_user.id,
        name=name,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=scopes
    )
    db.add(key_entry)
    db.commit()
    db.refresh(key_entry)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="CREATE_API_KEY",
        resource_type="APIKey",
        resource_id=str(key_entry.id),
        details=f"Generated API key '{name}' with scopes ({scopes})"
    )

    return {
        "id": key_entry.id,
        "name": key_entry.name,
        "key_prefix": prefix,
        "raw_secret": raw_secret,  # Only shown once
        "scopes": scopes,
        "created_at": key_entry.created_at.isoformat()
    }


@router.delete("/{id}", response_model=dict[str, Any])
def revoke_api_key(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Revoke API Key."""
    key = db.query(APIKey).filter(APIKey.id == id, APIKey.user_id == current_user.id).first()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")

    db.delete(key)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="REVOKE_API_KEY",
        resource_type="APIKey",
        resource_id=str(id),
        details=f"Revoked API key '{key.name}'"
    )

    return {"status": "revoked", "message": f"API Key #{id} revoked."}
