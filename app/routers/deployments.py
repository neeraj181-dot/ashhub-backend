from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.deployment import Deployment
from app.schemas.deployment import DeploymentCreate, DeploymentResponse, DeploymentTriggerResponse
from app.schemas.provider import ProviderResponse
from app.services.deployment_service import DeploymentService
from app.services.provider_factory import ProviderFactory
from app.auth.dependencies import get_current_active_user

router = APIRouter(prefix="/deployments", tags=["Deployments"])


def _format_deployment_response(dep: Deployment) -> DeploymentResponse:
    provider_resp = ProviderResponse.model_validate(dep.provider) if dep.provider else None
    return DeploymentResponse(
        id=dep.id,
        project_id=dep.project_id,
        provider_id=dep.provider_id,
        user_id=dep.user_id,
        status=dep.status,
        commit_hash=dep.commit_hash,
        branch=dep.branch,
        live_url=dep.live_url,
        provider=provider_resp,
        created_at=dep.created_at,
        updated_at=dep.updated_at
    )


@router.post("", response_model=DeploymentTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
def create_and_trigger_deployment(
    dep_in: DeploymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a deployment for a project using specified or auto-detected cloud provider.
    Frontend projects auto-route to Vercel; Backend projects auto-route to Oracle Cloud.
    Uses ProviderFactory abstraction.
    """
    deployment = DeploymentService.trigger_deployment(
        db=db,
        user_id=current_user.id,
        project_id=dep_in.project_id,
        provider_name=dep_in.provider_name,
        branch=dep_in.branch,
        commit_hash=dep_in.commit_hash
    )

    return DeploymentTriggerResponse(
        deployment_id=deployment.id,
        project_name=deployment.project.name if deployment.project else "Project",
        provider_name=deployment.provider.name if deployment.provider else "Cloud Provider",
        status=deployment.status,
        live_url=deployment.live_url,
        message=f"Deployment #{deployment.id} initiated successfully"
    )


@router.post("/{id}/trigger", response_model=DeploymentTriggerResponse)
def retrigger_deployment(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrigger an existing deployment."""
    dep = db.query(Deployment).filter(Deployment.id == id, Deployment.user_id == current_user.id).first()
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {id} not found"
        )

    provider_slug = dep.provider.slug if dep.provider else None
    new_deployment = DeploymentService.trigger_deployment(
        db=db,
        user_id=current_user.id,
        project_id=dep.project_id,
        provider_name=provider_slug,
        branch=dep.branch,
        commit_hash=dep.commit_hash
    )

    return DeploymentTriggerResponse(
        deployment_id=new_deployment.id,
        project_name=new_deployment.project.name if new_deployment.project else "Project",
        provider_name=new_deployment.provider.name if new_deployment.provider else "Cloud Provider",
        status=new_deployment.status,
        live_url=new_deployment.live_url,
        message=f"Re-deployment #{new_deployment.id} triggered successfully"
    )


@router.get("", response_model=list[DeploymentResponse])
def list_deployments(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all deployments for authenticated user."""
    deployments = db.query(Deployment).filter(Deployment.user_id == current_user.id).all()
    return [_format_deployment_response(d) for d in deployments]


@router.get("/{id}", response_model=DeploymentResponse)
def get_deployment(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get deployment details by ID."""
    dep = db.query(Deployment).filter(Deployment.id == id, Deployment.user_id == current_user.id).first()
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {id} not found"
        )
    return _format_deployment_response(dep)


@router.get("/{id}/health")
def check_deployment_health(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Execute health check against deployment's live URL via ProviderFactory."""
    dep = db.query(Deployment).filter(Deployment.id == id, Deployment.user_id == current_user.id).first()
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {id} not found"
        )

    if not dep.live_url:
        return {"deployment_id": dep.id, "healthy": False, "reason": "No live URL generated yet"}

    provider_slug = dep.provider.slug if dep.provider else "oracle"
    try:
        provider_instance = ProviderFactory.get(provider_slug)
        result = provider_instance.health_check(dep.live_url)
        return {"deployment_id": dep.id, **result}
    except Exception as e:
        return {"deployment_id": dep.id, "healthy": False, "error": str(e)}
