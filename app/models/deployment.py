from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    provider_id: Mapped[int] = mapped_column(Integer, ForeignKey("deployment_providers.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Queued")
    commit_hash: Mapped[str | None] = mapped_column(String(100), nullable=True)
    branch: Mapped[str] = mapped_column(String(100), default="main")
    live_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="deployments")
    provider: Mapped["DeploymentProvider"] = relationship("DeploymentProvider", back_populates="deployments")
    user: Mapped["User"] = relationship("User", back_populates="deployments")
    logs: Mapped[list["DeploymentLog"]] = relationship("DeploymentLog", back_populates="deployment", cascade="all, delete-orphan")
