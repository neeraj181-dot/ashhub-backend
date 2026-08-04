from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    deployment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., v1.2.0
    git_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    author: Mapped[str] = mapped_column(String(255), default="System")
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="published")  # published, rolled_back, draft
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project")
    deployment: Mapped[Optional["Deployment"]] = relationship("Deployment")
