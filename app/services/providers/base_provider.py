from abc import ABC, abstractmethod
from typing import Any
from app.core.enums import DeploymentStatus


class BaseDeploymentProvider(ABC):
    """
    Abstract Base Class defining the standard contract for all deployment providers.
    Providers like Vercel, Oracle Cloud, Render, Railway, Fly.io, AWS, etc.,
    must implement this interface.
    """

    def __init__(self, name: str, provider_type: str):
        self.name = name
        self.provider_type = provider_type

    @abstractmethod
    def deploy(self, project_name: str, repo_url: str, branch: str, env_vars: dict[str, str], config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Trigger a deployment operation.
        Returns a dictionary containing live_url, status, external_deployment_id, and message.
        """
        pass

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
        """Verify the health status of a deployed application URL."""
        pass
