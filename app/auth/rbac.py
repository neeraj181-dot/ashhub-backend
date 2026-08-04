from enum import Enum
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.organization import OrganizationMember


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


ROLE_HIERARCHY = {
    Role.OWNER: 4,
    Role.ADMIN: 3,
    Role.DEVELOPER: 2,
    Role.VIEWER: 1,
}

PERMISSIONS = {
    Role.OWNER: ["deploy", "delete", "rollback", "secrets", "domains", "billing", "runtime", "settings", "audit"],
    Role.ADMIN: ["deploy", "rollback", "secrets", "domains", "runtime", "settings", "audit"],
    Role.DEVELOPER: ["deploy", "rollback", "secrets", "runtime"],
    Role.VIEWER: ["read_only"],
}


def check_org_permission(db: Session, user_id: int, organization_id: int, required_permission: str) -> bool:
    """Verify if user has required RBAC permission within organization."""
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == user_id
    ).first()

    if not member:
        return False

    user_role = Role(member.role.lower())
    granted_permissions = PERMISSIONS.get(user_role, [])
    return required_permission in granted_permissions or user_role == Role.OWNER
