from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.repository import Repository
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.repository import RepositoryResponse
from app.auth.dependencies import get_current_active_user
from app.utils.encryption import encrypt_env_vars, decrypt_env_vars

router = APIRouter(prefix="/projects", tags=["Projects"])


def _format_project_response(project: Project) -> ProjectResponse:
    env_vars = decrypt_env_vars(project.environment_variables)
    repo_resp = RepositoryResponse.model_validate(project.repository) if project.repository else None
    return ProjectResponse(
        id=project.id,
        user_id=project.user_id,
        repository_id=project.repository_id,
        name=project.name,
        description=project.description,
        env_vars=env_vars,
        repository=repo_resp,
        created_at=project.created_at,
        updated_at=project.updated_at
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
        environment_variables=encrypted_envs
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
