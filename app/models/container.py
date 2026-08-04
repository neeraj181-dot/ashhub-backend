from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ContainerInstance(Base):
    __tablename__ = "container_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    deployment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    container_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    image_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running")  # running, stopped, restarted, exited
    cpu_pct: Mapped[float] = mapped_column(Float, default=1.2)
    memory_mb: Mapped[float] = mapped_column(Float, default=128.5)
    disk_mb: Mapped[float] = mapped_column(Float, default=45.0)
    ports_json: Mapped[Optional[str]] = mapped_column(Text, default='{"8000/tcp": 8000}')
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project")
    deployment: Mapped[Optional["Deployment"]] = relationship("Deployment")
