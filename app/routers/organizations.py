import secrets
from typing import Any, List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, OrganizationInvite
from app.auth.dependencies import get_current_active_user
from app.services.email_service import EmailService
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/organizations", tags=["Organizations & Teams"])


@router.get("", response_model=List[dict[str, Any]])
def list_user_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve organizations the user is a member of."""
    memberships = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).all()
    org_ids = [m.organization_id for m in memberships]

    orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all() if org_ids else []

    if not orgs:
        # Default user organization
        default_org = Organization(
            name=f"{current_user.full_name or 'Personal'}'s Org",
            slug=f"org-{current_user.id}-{secrets.token_hex(3)}",
            owner_id=current_user.id,
            plan="free",
            billing_status="active"
        )
        db.add(default_org)
        db.commit()
        db.refresh(default_org)

        mem = OrganizationMember(
            organization_id=default_org.id,
            user_id=current_user.id,
            role="owner"
        )
        db.add(mem)
        db.commit()
        orgs = [default_org]

    return [
        {
            "id": o.id,
            "name": o.name,
            "slug": o.slug,
            "owner_id": o.owner_id,
            "plan": o.plan,
            "billing_status": o.billing_status,
            "members_count": db.query(OrganizationMember).filter(OrganizationMember.organization_id == o.id).count(),
            "created_at": o.created_at.isoformat() if o.created_at else None
        }
        for o in orgs
    ]


@router.post("", response_model=dict[str, Any])
def create_organization(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Create a new multi-tenant Organization."""
    name = payload.get("name", "New Organization")
    slug = name.lower().replace(" ", "-").replace("_", "-") + f"-{secrets.token_hex(3)}"

    org = Organization(
        name=name,
        slug=slug,
        owner_id=current_user.id,
        plan="pro",
        billing_status="active"
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    mem = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role="owner"
    )
    db.add(mem)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="CREATE_ORGANIZATION",
        resource_type="Organization",
        resource_id=str(org.id),
        details=f"Created organization '{org.name}' ({org.slug})"
    )

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "owner_id": org.owner_id,
        "plan": org.plan,
        "billing_status": org.billing_status
    }


@router.get("/{id}/members", response_model=List[dict[str, Any]])
def list_organization_members(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """List team members within organization."""
    members = db.query(OrganizationMember).filter(OrganizationMember.organization_id == id).all()
    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "email": m.user.email if m.user else "user@example.com",
            "full_name": m.user.full_name if m.user else "Team Member",
            "role": m.role,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None
        }
        for m in members
    ]


@router.post("/{id}/invites", response_model=dict[str, Any])
def invite_team_member(
    id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Invite team member via email to Organization."""
    email = payload.get("email")
    role = payload.get("role", "developer")

    org = db.query(Organization).filter(Organization.id == id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    token = secrets.token_hex(24)
    invite = OrganizationInvite(
        organization_id=id,
        email=email,
        role=role,
        token=token,
        status="pending"
    )
    db.add(invite)
    db.commit()

    invite_link = f"http://localhost:3000/invites/accept?token={token}"
    EmailService.send_invite_email(email, org.name, invite_link, role)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="INVITE_MEMBER",
        resource_type="OrganizationInvite",
        resource_id=str(invite.id),
        details=f"Invited {email} as {role} to {org.name}"
    )

    return {
        "id": invite.id,
        "email": invite.email,
        "role": invite.role,
        "status": invite.status,
        "token": token,
        "invite_link": invite_link
    }
