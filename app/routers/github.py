from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository
from app.schemas.repository import RepositoryResponse, RepositorySelect
from app.services.github_service import GitHubService
from app.auth.dependencies import get_current_active_user

router = APIRouter(prefix="/github", tags=["GitHub Integration"])


@router.get("/connect")
def connect_github(
    token: str = "mock_github_access_token",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Connect user account with GitHub access token."""
    current_user.github_access_token = token
    db.commit()
    db.refresh(current_user)
    return {
        "status": "connected",
        "message": "GitHub account successfully connected",
        "github_access_token_configured": True
    }


@router.get("/repos", response_model=list[dict])
def fetch_user_repositories(
    current_user: User = Depends(get_current_active_user)
):
    """Fetch user's GitHub repositories."""
    return GitHubService.fetch_user_repositories(current_user.github_access_token)


@router.post("/select", response_model=RepositoryResponse)
def select_repository(
    selection: RepositorySelect,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Select a GitHub repository, auto-detect framework, and save metadata."""
    repo = GitHubService.select_repository(db, current_user.id, selection)
    return RepositoryResponse.model_validate(repo)


@router.get("/repos/{id}", response_model=RepositoryResponse)
def get_repository(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve saved repository details by ID."""
    repo = db.query(Repository).filter(Repository.id == id, Repository.user_id == current_user.id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {id} not found"
        )
    return RepositoryResponse.model_validate(repo)
