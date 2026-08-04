import hmac
import hashlib
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.project import Project
from app.models.preview import PreviewDeployment
from app.services.deployment_service import DeploymentService
from app.services.audit_service import log_audit_event
from app.services.notification_service import create_notification

router = APIRouter(prefix="/github/webhooks", tags=["GitHub Webhooks"])


@router.post("", response_model=dict[str, Any])
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header("push"),
    x_hub_signature_256: str | None = Header(None),
    db: Session = Depends(get_db)
) -> Any:
    """
    GitHub Webhook engine:
    Processes push, pull_request, release, and tag events, verifies X-Hub-Signature-256 HMAC,
    provisions PR preview environments, triggers automated deployments, and delivers notifications.
    """
    body = await request.body()

    # Webhook signature verification if secret is configured
    if settings.GITHUB_CLIENT_SECRET and x_hub_signature_256 and not settings.GITHUB_CLIENT_SECRET.startswith("mock_"):
        expected_sig = "sha256=" + hmac.new(
            settings.GITHUB_CLIENT_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, x_hub_signature_256):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = await request.json()
    repo_full_name = payload.get("repository", {}).get("full_name")

    if not repo_full_name:
        return {"status": "ignored", "reason": "No repository full_name in payload"}

    project = db.query(Project).join(Project.repository).filter(
        Project.repository.has(full_name=repo_full_name)
    ).first()

    if not project:
        return {"status": "ignored", "reason": f"No matching AshHub project registered for {repo_full_name}"}

    # Handle pull_request event
    if x_github_event == "pull_request":
        action = payload.get("action")
        pr_number = payload.get("number", 1)
        branch = payload.get("pull_request", {}).get("head", {}).get("ref", "feature/preview")
        commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha", "abc123def")

        if action in ["opened", "synchronize", "reopened"]:
            subdomain = branch.replace("/", "-").replace("_", "-").lower()[:20]
            preview_url = f"https://preview-{subdomain}-pr{pr_number}.ashhub.dev"

            preview = PreviewDeployment(
                project_id=project.id,
                pr_number=pr_number,
                branch=branch,
                commit_sha=commit_sha,
                preview_url=preview_url,
                status="active"
            )
            db.add(preview)
            db.commit()

            log_audit_event(
                db=db,
                user_id=project.user_id,
                action="WEBHOOK_PREVIEW_CREATED",
                resource_type="PreviewDeployment",
                resource_id=str(preview.id),
                details=f"Auto-provisioned preview environment for PR #{pr_number} ({preview_url})"
            )

            return {"status": "preview_created", "pr_number": pr_number, "preview_url": preview_url}

        elif action == "closed":
            db.query(PreviewDeployment).filter(
                PreviewDeployment.project_id == project.id,
                PreviewDeployment.pr_number == pr_number
            ).update({"status": "destroyed"})
            db.commit()

            return {"status": "preview_destroyed", "pr_number": pr_number}

    # Handle push, release, or tag events
    branch = payload.get("ref", "refs/heads/main").replace("refs/heads/", "")
    commit_sha = payload.get("after") or payload.get("head_commit", {}).get("id") or "main-sha"

    deployment = DeploymentService.trigger_deployment(
        db=db,
        user_id=project.user_id,
        project_id=project.id,
        branch=branch,
        commit_hash=commit_sha
    )

    log_audit_event(
        db=db,
        user_id=project.user_id,
        action="GITHUB_WEBHOOK_DEPLOY",
        resource_type="Deployment",
        resource_id=str(deployment.id),
        details=f"GitHub Webhook triggered deployment #{deployment.id} for {repo_full_name} ({branch})"
    )

    create_notification(
        db=db,
        user_id=project.user_id,
        title="Automated Deployment Triggered",
        message=f"Git push to {branch} triggered deployment #{deployment.id}.",
        notification_type="info"
    )

    return {
        "status": "triggered",
        "event": x_github_event,
        "deployment_id": deployment.id,
        "branch": branch,
        "commit_sha": commit_sha,
        "project": project.name
    }
