from typing import Any
import httpx
from app.core.enums import DeploymentStatus
from app.services.providers.base_provider import BaseDeploymentProvider


class VercelProvider(BaseDeploymentProvider):
    """
    Vercel Deployment Provider implementation for frontend applications.
    Follows provider abstraction specification.
    """

    def __init__(self):
        super().__init__(name="Vercel", provider_type="frontend")

    def deploy(
        self,
        project_name: str,
        repo_url: str,
        branch: str,
        env_vars: dict[str, str],
        config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Skeleton deployment logic for Vercel.
        In production, this calls Vercel API `/v13/deployments`.
        """
        subdomain = project_name.lower().replace(" ", "-").replace("_", "-")
        live_url = f"https://{subdomain}.vercel.app"

        return {
            "external_deployment_id": f"vcl_{subdomain}_101",
            "status": DeploymentStatus.RUNNING,
            "live_url": live_url,
            "message": f"Successfully deployed {project_name} to Vercel",
            "provider": self.name
        }

    def status(self, external_deployment_id: str) -> DeploymentStatus:
        return DeploymentStatus.RUNNING

    def logs(self, external_deployment_id: str) -> list[str]:
        return [
            f"[Vercel] Build initiated for {external_deployment_id}",
            "[Vercel] Installing dependencies (npm install)...",
            "[Vercel] Building static assets (npm run build)...",
            "[Vercel] Deploying build artifacts to Vercel Edge Network...",
            "[Vercel] Deployment live!"
        ]

    def health_check(self, live_url: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(live_url)
                healthy = response.status_code < 400
                return {"healthy": healthy, "status_code": response.status_code, "url": live_url}
        except Exception as e:
            return {"healthy": False, "error": str(e), "url": live_url}
