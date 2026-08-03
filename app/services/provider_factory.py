from typing import Type
from app.services.providers.base_provider import BaseDeploymentProvider
from app.services.providers.vercel_provider import VercelProvider
from app.services.providers.oracle_provider import OracleProvider


class ProviderFactory:
    """
    Factory pattern class for dynamic deployment provider resolution.
    Encapsulates creation of deployment providers so business logic (DeploymentService)
    never couples directly to specific cloud providers.
    """

    _registry: dict[str, Type[BaseDeploymentProvider]] = {}

    @classmethod
    def register_provider(cls, key: str, provider_cls: Type[BaseDeploymentProvider]) -> None:
        """Register a new deployment provider with the factory."""
        cls._registry[key.lower().strip()] = provider_cls

    @classmethod
    def get(cls, provider_name: str) -> BaseDeploymentProvider:
        """
        Instantiate and return the requested deployment provider.
        Raises ValueError if the provider is not registered.
        """
        normalized_name = provider_name.lower().strip().replace(" ", "_").replace("-", "_")
        
        # Check standard normalized key or original key
        provider_cls = cls._registry.get(normalized_name) or cls._registry.get(provider_name.lower().strip())
        
        if not provider_cls:
            available = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown provider '{provider_name}'. Available providers: {available}")
            
        return provider_cls()

    @classmethod
    def list_available(cls) -> list[str]:
        """List all currently registered provider keys."""
        return sorted(list(cls._registry.keys()))


# Default auto-registration of built-in providers
ProviderFactory.register_provider("vercel", VercelProvider)
ProviderFactory.register_provider("oracle", OracleProvider)
ProviderFactory.register_provider("oracle_cloud", OracleProvider)
ProviderFactory.register_provider("oracle cloud", OracleProvider)
