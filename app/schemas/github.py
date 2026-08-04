from typing import Any, Optional
from pydantic import BaseModel


class GitHubProfileResponse(BaseModel):
    id: Optional[int | str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    connected: bool = False


class GitHubRepoResponse(BaseModel):
    github_id: Optional[int] = None
    name: str
    owner: str
    full_name: str
    clone_url: str
    visibility: str = "public"
    private: bool = False
    default_branch: str = "main"
    language: Optional[str] = None
    last_updated: Optional[str] = None
    stars: int = 0


class GitHubBranchResponse(BaseModel):
    name: str
    commit_sha: Optional[str] = None
    protected: bool = False


class GitHubContentItem(BaseModel):
    name: str
    path: str
    type: str  # file or dir
    size: Optional[int] = None
    download_url: Optional[str] = None


class AnalysisResult(BaseModel):
    frontend: Optional[str] = None
    backend: Optional[str] = None
    database: Optional[str] = None
    docker: bool = False
    github_actions: bool = False
    recommendedFrontendProvider: Optional[str] = None
    recommendedBackendProvider: Optional[str] = None
