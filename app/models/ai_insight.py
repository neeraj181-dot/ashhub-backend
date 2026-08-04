from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AIDeploymentInsight(Base):
    __tablename__ = "ai_deployment_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    deployment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)  # failure_analysis, docker_review, env_check, cost_optimization, security_scan, health_score
    health_score: Mapped[float] = mapped_column(Float, default=92.0)
    analysis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    suggestions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project")
    deployment: Mapped[Optional["Deployment"]] = relationship("Deployment")
