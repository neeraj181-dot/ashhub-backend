from typing import Any


class EmailService:
    """Transactional HTML email notification template builder."""

    @staticmethod
    def send_invite_email(to_email: str, org_name: str, invite_link: str, role: str) -> dict[str, Any]:
        html_content = f"""
        <div style="font-family: monospace; background: #000; color: #fff; padding: 24px; border-radius: 12px;">
            <h2 style="color: #38bdf8;">AshHub Organization Invitation</h2>
            <p>You have been invited to join <strong>{org_name}</strong> as a <strong>{role.upper()}</strong>.</p>
            <p><a href="{invite_link}" style="background: #fff; color: #000; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-weight: bold;">Accept Invite</a></p>
        </div>
        """
        return {"status": "sent", "to": to_email, "subject": f"Invitation to join {org_name} on AshHub"}

    @staticmethod
    def send_deployment_alert(to_email: str, project_name: str, status: str, live_url: str | None = None) -> dict[str, Any]:
        return {
            "status": "sent",
            "to": to_email,
            "subject": f"Deployment {status.upper()}: {project_name}"
        }
