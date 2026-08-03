from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.core.enums import DeploymentStatus
from app.schemas.provider import ProviderResponse


class DeploymentCreate(BaseModel):
    project_id: int
    provider_id: int | None = None
    provider_name: str | None = None  # e.g., "vercel" or "oracle"
    commit_hash: str | None = None
    branch: str = "main"


class DeploymentTriggerResponse(BaseModel):
    deployment_id: int
    project_name: str
    provider_name: str
    status: DeploymentStatus
    live_url: str | None = None
    message: str


class DeploymentResponse(BaseModel):
    id: int
    project_id: int
    provider_id: int
    user_id: int
    status: DeploymentStatus
    commit_hash: str | None = None
    branch: str
    live_url: str | None = None
    provider: ProviderResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
