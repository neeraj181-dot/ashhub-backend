import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.provider import DeploymentProvider
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderResponse
from app.services.provider_factory import ProviderFactory
from app.auth.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/providers", tags=["Deployment Providers"])


def _format_provider_response(provider: DeploymentProvider) -> ProviderResponse:
    config_dict = json.loads(provider.config) if provider.config else None
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        slug=provider.slug,
        provider_type=provider.provider_type,
        config=config_dict,
        is_active=provider.is_active,
        created_at=provider.created_at,
        updated_at=provider.updated_at
    )


@router.get("", response_model=list[ProviderResponse])
def list_providers(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all registered deployment providers."""
    providers = db.query(DeploymentProvider).all()
    if not providers:
        # Seed default providers if none exist in database
        defaults = [
            {"name": "Vercel", "slug": "vercel", "provider_type": "frontend"},
            {"name": "Oracle Cloud", "slug": "oracle", "provider_type": "backend"},
            {"name": "Render", "slug": "render", "provider_type": "both"},
            {"name": "Railway", "slug": "railway", "provider_type": "both"},
            {"name": "Fly.io", "slug": "fly", "provider_type": "both"},
            {"name": "AWS", "slug": "aws", "provider_type": "both"}
        ]
        for d in defaults:
            p = DeploymentProvider(**d)
            db.add(p)
        db.commit()
        providers = db.query(DeploymentProvider).all()

    return [_format_provider_response(p) for p in providers]


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
def create_provider(
    prov_in: ProviderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Register a new deployment provider in database."""
    existing = db.query(DeploymentProvider).filter(
        (DeploymentProvider.slug == prov_in.slug) | (DeploymentProvider.name == prov_in.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider with name/slug '{prov_in.name}' already exists"
        )

    config_json = json.dumps(prov_in.config) if prov_in.config else None
    provider = DeploymentProvider(
        name=prov_in.name,
        slug=prov_in.slug.lower().strip(),
        provider_type=prov_in.provider_type.value,
        config=config_json,
        is_active=prov_in.is_active
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return _format_provider_response(provider)


@router.get("/{id}", response_model=ProviderResponse)
def get_provider(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get provider details by ID."""
    provider = db.query(DeploymentProvider).filter(DeploymentProvider.id == id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with ID {id} not found"
        )
    return _format_provider_response(provider)


@router.put("/{id}", response_model=ProviderResponse)
def update_provider(
    id: int,
    prov_in: ProviderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update provider configuration or status."""
    provider = db.query(DeploymentProvider).filter(DeploymentProvider.id == id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with ID {id} not found"
        )

    if prov_in.name is not None:
        provider.name = prov_in.name
    if prov_in.provider_type is not None:
        provider.provider_type = prov_in.provider_type.value
    if prov_in.config is not None:
        provider.config = json.dumps(prov_in.config)
    if prov_in.is_active is not None:
        provider.is_active = prov_in.is_active

    db.commit()
    db.refresh(provider)
    return _format_provider_response(provider)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a deployment provider."""
    provider = db.query(DeploymentProvider).filter(DeploymentProvider.id == id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with ID {id} not found"
        )
    db.delete(provider)
    db.commit()
    return None
