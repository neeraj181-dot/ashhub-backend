from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DeploymentStage(Base):
    __tablename__ = "deployment_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    deployment_id: Mapped[int] = mapped_column(Integer, ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(50), nullable=False)  # QUEUED, BUILDING, UPLOADING, PROVISIONING, STARTING, HEALTH_CHECK, RUNNING
    status: Mapped[str] = mapped_column(String(30), default="in_progress")  # pending, in_progress, completed, failed, skipped
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deployment: Mapped["Deployment"] = relationship("Deployment")
