from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.services.notification_service import get_user_notifications

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[dict[str, Any]])
def list_notifications(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Retrieve recent notifications for the authenticated user."""
    notifications = get_user_notifications(db, current_user.id, limit=limit)
    res = []
    for n in notifications:
        created_str = None
        if n.created_at:
            if isinstance(n.created_at, str):
                created_str = n.created_at
            elif hasattr(n.created_at, "isoformat"):
                created_str = n.created_at.isoformat()
            else:
                created_str = str(n.created_at)

        res.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type,
            "is_read": bool(n.is_read),
            "created_at": created_str,
        })
    return res


@router.post("/read-all", response_model=dict[str, Any])
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Mark all unread notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "success", "message": "All notifications marked as read."}
