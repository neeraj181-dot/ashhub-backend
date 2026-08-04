from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.repository import RepositoryResponse


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    env_vars: dict[str, str] = {}
    is_favorite: bool = False
    build_command: str | None = None
    start_command: str | None = None
    install_command: str | None = None
    output_dir: str | None = None
    health_check_path: str | None = None


class ProjectCreate(ProjectBase):
    repository_id: int


class ProjectImport(BaseModel):
    owner: str | None = None
    repo: str | None = None
    repository: str | None = None
    branch: str | None = "main"
    name: str | None = None
    description: str | None = None
    env_vars: dict[str, str] = {}
    is_favorite: bool = False
    build_command: str | None = None
    start_command: str | None = None
    install_command: str | None = None
    output_dir: str | None = None
    health_check_path: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    env_vars: dict[str, str] | None = None
    is_favorite: bool | None = None
    build_command: str | None = None
    start_command: str | None = None
    install_command: str | None = None
    output_dir: str | None = None
    health_check_path: str | None = None


class ProjectResponse(BaseModel):
    id: int
    user_id: int
    repository_id: int
    name: str
    description: str | None = None
    env_vars: dict[str, str] = {}
    is_favorite: bool = False
    build_command: str | None = None
    start_command: str | None = None
    install_command: str | None = None
    output_dir: str | None = None
    health_check_path: str | None = None
    repository: RepositoryResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
