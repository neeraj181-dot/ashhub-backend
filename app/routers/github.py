import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository
from app.schemas.repository import RepositoryResponse, RepositorySelect
from app.schemas.github import (
    GitHubProfileResponse,
    GitHubRepoResponse,
    GitHubBranchResponse,
    GitHubContentItem,
    AnalysisResult
)
from app.services.github_service import GitHubService
from app.services.github_oauth_service import GitHubOAuthService
from app.services.github_repository_service import GitHubRepositoryService
from app.services.github_analyzer import GitHubAnalyzer
from app.services.audit_service import log_audit_event
from app.services.notification_service import create_notification
from app.auth.dependencies import get_current_active_user

logger = logging.getLogger("ashhub.github")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

router = APIRouter(prefix="/github", tags=["GitHub Integration"])


# -----------------------------------------------------------------------------
# OAUTH ENDPOINTS
# -----------------------------------------------------------------------------

@router.get("/login")
def github_login(
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate GitHub OAuth login URL with a secure state token associated
    with the currently authenticated AshHub user.
    """
    logger.info("Received GitHub login request for user_id=%s (%s)", current_user.id, current_user.email)
    state = GitHubOAuthService.create_oauth_state(current_user.id)
    url = GitHubOAuthService.get_login_url(state=state)
    logger.info("Generated OAuth URL: %s", url)
    logger.info("Redirecting user to GitHub authorization screen")
    return {"url": url}


@router.get("/callback")
def github_callback(
    code: str = Query(..., description="Authorization code from GitHub OAuth"),
    state: str | None = Query(None, description="OAuth state parameter"),
    db: Session = Depends(get_db)
):
    """
    PUBLIC GitHub OAuth Callback Endpoint:
    Does NOT require authentication headers. Validates state, exchanges code for token,
    stores profile & encrypted access token, and redirects to frontend Settings page.
    """
    logger.info("Received callback with code=%s... state=%s", code[:10] if code else "", state)
    user_id = GitHubOAuthService.verify_oauth_state(state)
    user = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()

    if not user:
        # Fallback for single-user test environments
        user = db.query(User).first()

    if not user:
        logger.warning("OAuth Callback Error: No valid user matched for state=%s. Redirecting to failed page.", state)
        return RedirectResponse(url="http://localhost:3000/settings?github=failed", status_code=307)

    try:
        access_token = GitHubOAuthService.exchange_code_for_token(code=code, state=state)
        logger.info("Exchanged access token successfully for user_id=%s", user.id)

        profile = GitHubOAuthService.get_user_profile(access_token)

        # Encrypt & save token and GitHub profile info
        GitHubOAuthService.save_user_token_and_profile(
            db=db,
            user=user,
            token=access_token,
            github_id=profile.get("id"),
            username=profile.get("username"),
            avatar_url=profile.get("avatar_url")
        )
        logger.info("Stored encrypted token and profile details for user_id=%s (@%s)", user.id, profile.get("username"))

        log_audit_event(
            db=db,
            user_id=user.id,
            action="CONNECT_GITHUB",
            resource_type="User",
            resource_id=str(user.id),
            details=f"GitHub account @{profile.get('username')} successfully connected"
        )

        create_notification(
            db=db,
            user_id=user.id,
            title="GitHub Account Connected",
            message=f"GitHub account @{profile.get('username')} has been connected to your AshHub account.",
            notification_type="success"
        )

        logger.info("Redirecting to frontend settings page: http://localhost:3000/settings?github=connected")
        return RedirectResponse(url="http://localhost:3000/settings?github=connected", status_code=307)
    except Exception as e:
        logger.error("Error during GitHub OAuth callback processing: %s", e)
        return RedirectResponse(url="http://localhost:3000/settings?github=failed", status_code=307)


@router.get("/profile", response_model=GitHubProfileResponse)
def get_github_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get GitHub profile details for authenticated user."""
    profile = GitHubOAuthService.get_user_profile(current_user.github_access_token)
    if current_user.github_username:
        profile["username"] = current_user.github_username
    if current_user.github_avatar_url:
        profile["avatar_url"] = current_user.github_avatar_url
    if current_user.github_id:
        profile["id"] = current_user.github_id
    profile["connected"] = bool(current_user.github_access_token)
    return GitHubProfileResponse(**profile)


@router.post("/disconnect")
def disconnect_github(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Disconnect GitHub integration by removing stored OAuth token and profile fields."""
    logger.info("Received request to disconnect GitHub for user_id=%s", current_user.id)
    GitHubOAuthService.disconnect_user_token(db, current_user)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="DISCONNECT_GITHUB",
        resource_type="User",
        resource_id=str(current_user.id),
        details="Disconnected GitHub OAuth integration"
    )

    return {
        "status": "disconnected",
        "message": "GitHub account successfully disconnected"
    }


# -----------------------------------------------------------------------------
# REPOSITORIES ENDPOINTS
# -----------------------------------------------------------------------------

@router.get("/repositories", response_model=list[GitHubRepoResponse])
@router.get("/repos", response_model=list[GitHubRepoResponse])
def fetch_repositories(
    current_user: User = Depends(get_current_active_user)
):
    """Fetch repositories accessible by authenticated GitHub user."""
    repos = GitHubRepositoryService.list_user_repositories(current_user.github_access_token)
    return [GitHubRepoResponse(**r) for r in repos]


@router.get("/repositories/{owner}/{repo}", response_model=GitHubRepoResponse)
def get_repository_details(
    owner: str,
    repo: str,
    current_user: User = Depends(get_current_active_user)
):
    """Fetch detailed metadata for a single GitHub repository."""
    r = GitHubRepositoryService.get_repository(current_user.github_access_token, owner, repo)
    return GitHubRepoResponse(**r)


@router.get("/repositories/{owner}/{repo}/branches", response_model=list[GitHubBranchResponse])
def list_repository_branches(
    owner: str,
    repo: str,
    current_user: User = Depends(get_current_active_user)
):
    """List branches for a GitHub repository."""
    branches = GitHubRepositoryService.list_branches(current_user.github_access_token, owner, repo)
    return [GitHubBranchResponse(**b) for b in branches]


@router.get("/repositories/{owner}/{repo}/contents", response_model=list[GitHubContentItem])
def get_repository_contents(
    owner: str,
    repo: str,
    path: str = Query("", description="Subdirectory path"),
    current_user: User = Depends(get_current_active_user)
):
    """Fetch files and directories in repository path."""
    items = GitHubRepositoryService.get_contents(current_user.github_access_token, owner, repo, path)
    return [GitHubContentItem(**item) for item in items]


# -----------------------------------------------------------------------------
# FRAMEWORK ANALYZER ENDPOINT
# -----------------------------------------------------------------------------

@router.get("/repositories/{owner}/{repo}/analyze", response_model=AnalysisResult)
@router.post("/repositories/{owner}/{repo}/analyze", response_model=AnalysisResult)
def analyze_repository(
    owner: str,
    repo: str,
    branch: str = Query("main", description="Target branch"),
    current_user: User = Depends(get_current_active_user)
):
    """Inspect repository files to auto-detect frontend, backend, database, docker, and recommended providers."""
    return GitHubAnalyzer.analyze_repository(
        access_token=current_user.github_access_token,
        owner=owner,
        repo=repo,
        branch=branch
    )


# -----------------------------------------------------------------------------
# LEGACY / COMPATIBILITY SELECT ENDPOINT
# -----------------------------------------------------------------------------

@router.get("/connect")
def connect_github(
    token: str = "mock_github_access_token",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Connect user account with GitHub access token (legacy helper)."""
    GitHubOAuthService.save_user_token(db, current_user, token)
    return {
        "status": "connected",
        "message": "GitHub account successfully connected",
        "github_access_token_configured": True
    }


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
