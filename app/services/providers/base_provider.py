from abc import ABC, abstractmethod
from typing import Any
from app.core.enums import DeploymentStatus


class BaseDeploymentProvider(ABC):
    """
    Abstract Base Class defining the standard contract for all deployment providers.
    Every provider (Vercel, Render, Railway, Fly.io, Netlify, Neon, Supabase, Oracle Cloud)
    must implement this standard interface.
    """

    def __init__(self, name: str, provider_type: str):
        self.name = name
        self.provider_type = provider_type  # 'frontend', 'backend', 'database', 'storage'

    def connect(self, credentials: dict[str, Any] | None = None) -> bool:
        """Verify provider authentication token and connection status."""
        return True

    def validate(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate component settings, environment variables, and build configuration."""
        return {"valid": True, "provider": self.name}

    def create_project(self, project_name: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Provision remote project namespace or database instance."""
        clean_name = project_name.lower().replace(" ", "-").replace("_", "-")
        return {"id": f"prj_{clean_name}", "name": clean_name, "provider": self.name}

    @abstractmethod
    def deploy(
        self,
        project_name: str,
        repo_url: str,
        branch: str,
        env_vars: dict[str, str],
        config: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Trigger a deployment operation.
        Returns a dictionary containing live_url, status, external_deployment_id, and message.
        """
        pass

    def poll_status(self, external_deployment_id: str) -> DeploymentStatus:
        """Poll current execution state from remote provider."""
        return self.status(external_deployment_id)

    @abstractmethod
    def status(self, external_deployment_id: str) -> DeploymentStatus:
        """Query the current deployment status from the remote provider."""
        pass

    @abstractmethod
    def logs(self, external_deployment_id: str) -> list[str]:
        """Fetch execution and build logs from the provider."""
        pass

    @abstractmethod
    def health_check(self, live_url: str) -> dict[str, Any]:
        """Verify the health status of a deployed application URL or database connection."""
        pass

    def destroy(self, external_deployment_id: str) -> bool:
        """Tear down or suspend remote service."""
        return True
