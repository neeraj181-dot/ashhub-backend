from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.core.enums import FrameworkType


class RepositoryBase(BaseModel):
    name: str
    full_name: str
    clone_url: str
    default_branch: str = "main"
    framework: FrameworkType = FrameworkType.UNKNOWN


class RepositoryCreate(RepositoryBase):
    github_id: int | None = None


class RepositorySelect(BaseModel):
    github_id: int | None = None
    name: str
    full_name: str
    clone_url: str
    default_branch: str = "main"
    framework: FrameworkType | None = None


class RepositoryResponse(RepositoryBase):
    id: int
    user_id: int
    github_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
