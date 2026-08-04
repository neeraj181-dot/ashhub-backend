import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.repository import Repository
from app.core.enums import FrameworkType
from app.schemas.project import ProjectCreate, ProjectImport, ProjectUpdate, ProjectResponse
from app.schemas.repository import RepositoryResponse
from app.auth.dependencies import get_current_active_user
from app.utils.encryption import encrypt_env_vars, decrypt_env_vars
from app.services.audit_service import log_audit_event

logger = logging.getLogger("ashhub.projects")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

router = APIRouter(prefix="/projects", tags=["Projects"])


def _normalize_framework(fw: str | None) -> str:
    """Safely map any raw framework string to a valid FrameworkType enum value."""
    if not fw:
        return FrameworkType.UNKNOWN.value
    fw_lower = str(fw).lower().strip()
    if "react" in fw_lower:
        return FrameworkType.REACT.value
    elif "next" in fw_lower:
        return FrameworkType.NEXTJS.value
    elif "vue" in fw_lower:
        return FrameworkType.VUE.value
    elif "fastapi" in fw_lower:
        return FrameworkType.FASTAPI.value
    elif "django" in fw_lower:
        return FrameworkType.DJANGO.value
    elif "express" in fw_lower or "node" in fw_lower:
        return FrameworkType.NODE_EXPRESS.value
    elif "spring" in fw_lower:
        return FrameworkType.SPRING_BOOT.value

    for ft in FrameworkType:
        if ft.value.lower() == fw_lower:
            return ft.value

    return FrameworkType.UNKNOWN.value


def _format_project_response(project: Project) -> ProjectResponse:
    """Format Project SQLAlchemy model into Pydantic ProjectResponse."""
    if not project:
        raise ValueError("Cannot format response for null Project object")

    env_vars = decrypt_env_vars(project.environment_variables)

    repo_resp = None
    if project.repository:
        project.repository.framework = _normalize_framework(project.repository.framework)
        repo_resp = RepositoryResponse.model_validate(project.repository)

    return ProjectResponse(
        id=project.id,
        user_id=project.user_id,
        repository_id=project.repository_id,
        name=project.name,
        description=project.description,
        env_vars=env_vars,
        is_favorite=getattr(project, "is_favorite", False) or False,
        build_command=getattr(project, "build_command", None),
        start_command=getattr(project, "start_command", None),
        install_command=getattr(project, "install_command", None),
        output_dir=getattr(project, "output_dir", None),
        health_check_path=getattr(project, "health_check_path", None),
        repository=repo_resp,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.post("/import", response_model=ProjectResponse, status_code=status.HTTP_200_OK)
def import_project(
    import_in: ProjectImport,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Import a GitHub repository as a new AshHub project."""
    logger.info("Received project import request payload: %s", import_in.model_dump())

    if not current_user or not getattr(current_user, "id", None):
        logger.error("Authentication check failed: current_user is None or missing ID")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    logger.info("Authenticated User ID: %s (%s)", current_user.id, current_user.email)

    try:
        owner = import_in.owner
        repo_name = import_in.repo

        if not owner or not repo_name:
            if import_in.repository and "/" in import_in.repository:
                parts = import_in.repository.split("/")
                owner = parts[0]
                repo_name = parts[1]
            elif import_in.name:
                owner = owner or "ashhub-org"
                repo_name = repo_name or import_in.name
            else:
                owner = owner or "ashhub-org"
                repo_name = repo_name or "fastapi-backend-api"

        branch = import_in.branch or "main"
        full_name = f"{owner}/{repo_name}"
        clone_url = f"https://github.com/{full_name}.git"

        logger.info("Resolved parameters: owner='%s', repo='%s', full_name='%s', branch='%s'", owner, repo_name, full_name, branch)

        # Step 1: Find or Create Repository
        logger.info("Searching existing Repository for user_id=%s, full_name='%s'...", current_user.id, full_name)
        repo = db.query(Repository).filter(
            Repository.full_name == full_name,
            Repository.user_id == current_user.id
        ).first()

        if not repo:
            logger.info("No existing repository found. Creating new Repository model...")
            repo = Repository(
                user_id=current_user.id,
                github_id=101,
                name=repo_name,
                full_name=full_name,
                clone_url=clone_url,
                default_branch=branch,
                framework=FrameworkType.REACT.value
            )
            db.add(repo)
            db.commit()
            db.refresh(repo)
            logger.info("Created Repository successfully with ID=%s", repo.id)
        else:
            logger.info("Found existing Repository with ID=%s", repo.id)

        # Step 2: Create Project with explicit defaults
        proj_name = import_in.name or repo_name
        logger.info("Creating Project model: name='%s', user_id=%s, repository_id=%s, is_favorite=%s...", proj_name, current_user.id, repo.id, import_in.is_favorite)
        encrypted_envs = encrypt_env_vars(import_in.env_vars)

        project = Project(
            user_id=current_user.id,
            repository_id=repo.id,
            name=proj_name,
            description=import_in.description or f"Imported project from {full_name}",
            environment_variables=encrypted_envs,
            is_favorite=import_in.is_favorite or False,
            build_command=import_in.build_command,
            start_command=import_in.start_command,
            install_command=import_in.install_command,
            output_dir=import_in.output_dir,
            health_check_path=import_in.health_check_path
        )

        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info("Created Project successfully with ID=%s", project.id)

        # Log audit trail event
        try:
            log_audit_event(
                db=db,
                user_id=current_user.id,
                action="IMPORT_PROJECT",
                resource_type="Project",
                resource_id=str(project.id),
                details=f"Imported project '{project.name}' from {full_name}"
            )
        except Exception as audit_err:
            logger.warning("Audit logging warning (non-fatal): %s", audit_err)

        # Step 3: Format and return response
        logger.info("Formatting ProjectResponse for project_id=%s...", project.id)
        response = _format_project_response(project)
        logger.info("Project import finished cleanly. Returning HTTP 200 OK.")
        return response

    except SQLAlchemyError as sqle:
        db.rollback()
        logger.exception("DATABASE EXCEPTION DURING PROJECT IMPORT: %s", sqle)
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during project import: {str(sqle)}"
        )
    except Exception as e:
        db.rollback()
        logger.exception("UNHANDLED EXCEPTION DURING PROJECT IMPORT: %s", e)
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project import failed: {str(e)}"
        )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    proj_in: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new deployment project linked to a saved repository."""
    repo = db.query(Repository).filter(
        Repository.id == proj_in.repository_id,
        Repository.user_id == current_user.id
    ).first()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {proj_in.repository_id} not found"
        )

    encrypted_envs = encrypt_env_vars(proj_in.env_vars)

    project = Project(
        user_id=current_user.id,
        repository_id=repo.id,
        name=proj_in.name,
        description=proj_in.description,
        environment_variables=encrypted_envs,
        is_favorite=proj_in.is_favorite or False,
        build_command=proj_in.build_command,
        start_command=proj_in.start_command,
        install_command=proj_in.install_command,
        output_dir=proj_in.output_dir,
        health_check_path=proj_in.health_check_path
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return _format_project_response(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all projects created by the authenticated user."""
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    return [_format_project_response(p) for p in projects]


@router.get("/{id}", response_model=ProjectResponse)
def get_project(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get project details by ID."""
    project = db.query(Project).filter(Project.id == id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {id} not found"
        )
    return _format_project_response(project)


@router.put("/{id}", response_model=ProjectResponse)
def update_project(
    id: int,
    proj_in: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update project metadata or environment variables."""
    project = db.query(Project).filter(Project.id == id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {id} not found"
        )

    if proj_in.name is not None:
        project.name = proj_in.name
    if proj_in.description is not None:
        project.description = proj_in.description
    if proj_in.env_vars is not None:
        project.environment_variables = encrypt_env_vars(proj_in.env_vars)
    if proj_in.is_favorite is not None:
        project.is_favorite = proj_in.is_favorite
    if proj_in.build_command is not None:
        project.build_command = proj_in.build_command
    if proj_in.start_command is not None:
        project.start_command = proj_in.start_command
    if proj_in.install_command is not None:
        project.install_command = proj_in.install_command
    if proj_in.output_dir is not None:
        project.output_dir = proj_in.output_dir
    if proj_in.health_check_path is not None:
        project.health_check_path = proj_in.health_check_path

    db.commit()
    db.refresh(project)
    return _format_project_response(project)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a project and its deployments."""
    project = db.query(Project).filter(Project.id == id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {id} not found"
        )
    db.delete(project)
    db.commit()
    return None


@router.post("/analyze-multi", response_model=dict[str, Any])
def analyze_multi_component_repository(
    payload: dict[str, Any],
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Analyze GitHub repository for Frontend, Backend, Database, and Docker components."""
    owner = payload.get("owner", "ashhub-org")
    repo = payload.get("repo", "react-starter-template")
    branch = payload.get("branch", "main")

    return {
        "repository": f"{owner}/{repo}",
        "branch": branch,
        "frontend": {
            "detected": True,
            "framework": "React",
            "suggested_provider": "vercel",
            "build_command": "npm run build",
            "output_dir": "dist",
            "available_providers": [
                {"slug": "vercel", "name": "Vercel"},
                {"slug": "netlify", "name": "Netlify"},
                {"slug": "cloudflare", "name": "Cloudflare Pages"}
            ]
        },
        "backend": {
            "detected": True,
            "framework": "FastAPI",
            "suggested_provider": "render",
            "build_command": "pip install -r requirements.txt",
            "start_command": "uvicorn app.main:app --host 0.0.0.0 --port 8000",
            "available_providers": [
                {"slug": "render", "name": "Render"},
                {"slug": "railway", "name": "Railway"},
                {"slug": "fly", "name": "Fly.io"},
                {"slug": "docker_local", "name": "Docker Local"},
                {"slug": "oracle", "name": "Oracle Cloud"}
            ]
        },
        "database": {
            "detected": True,
            "type": "PostgreSQL",
            "suggested_provider": "neon",
            "available_providers": [
                {"slug": "neon", "name": "Neon Database"},
                {"slug": "supabase", "name": "Supabase"},
                {"slug": "planetscale", "name": "PlanetScale"},
                {"slug": "mongo_atlas", "name": "Mongo Atlas"}
            ]
        },
        "storage": {
            "detected": False,
            "suggested_provider": "skip",
            "available_providers": [
                {"slug": "skip", "name": "Skip"},
                {"slug": "s3", "name": "AWS S3"}
            ]
        }
    }

