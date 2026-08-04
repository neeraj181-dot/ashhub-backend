from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    repository_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    environment_variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted JSON
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    build_command: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_command: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    install_command: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    output_dir: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    health_check_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    repository: Mapped["Repository"] = relationship("Repository", back_populates="projects")
    deployments: Mapped[list["Deployment"]] = relationship("Deployment", back_populates="project", cascade="all, delete-orphan")
