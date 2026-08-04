from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DockerArtifact(Base):
    __tablename__ = "docker_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    deployment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    image_tag: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    digest: Mapped[str] = mapped_column(String(128), nullable=False)  # sha256:abc...
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    sbom_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project")
    deployment: Mapped[Optional["Deployment"]] = relationship("Deployment")
