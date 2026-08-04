from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
) -> Notification:
    """Create and persist a user notification."""
    noti = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
    )
    db.add(noti)
    db.commit()
    db.refresh(noti)
    return noti


def get_user_notifications(db: Session, user_id: int, limit: int = 20) -> List[Notification]:
    """Retrieve recent notifications for a user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
