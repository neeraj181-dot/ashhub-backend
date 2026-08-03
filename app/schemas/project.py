from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.repository import RepositoryResponse


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    env_vars: dict[str, str] = {}


class ProjectCreate(ProjectBase):
    repository_id: int


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    env_vars: dict[str, str] | None = None


class ProjectResponse(BaseModel):
    id: int
    user_id: int
    repository_id: int
    name: str
    description: str | None = None
    env_vars: dict[str, str] = {}
    repository: RepositoryResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
