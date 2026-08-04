from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/activity", tags=["Activity Feed"])


@router.get("", response_model=List[dict[str, Any]])
def get_activity_feed(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Retrieve global activity feed events for the workspace."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": l.id,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "details": l.details,
            "actor": current_user.full_name or current_user.email,
            "timestamp": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
