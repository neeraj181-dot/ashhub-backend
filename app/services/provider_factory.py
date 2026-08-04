from typing import Type, Any
from app.core.enums import FrameworkType
from app.services.providers.base_provider import BaseDeploymentProvider
from app.services.providers.vercel_provider import VercelProvider
from app.services.providers.oracle_provider import OracleProvider
from app.services.providers.render_provider import RenderProvider
from app.services.providers.railway_provider import RailwayProvider
from app.services.providers.fly_provider import FlyProvider
from app.services.providers.netlify_provider import NetlifyProvider
from app.services.providers.neon_provider import NeonProvider
from app.services.providers.supabase_provider import SupabaseProvider
from app.services.providers.docker_local_provider import DockerLocalProvider


class ProviderFactory:
    """Factory for instantiating and managing cloud deployment providers."""

    _providers: dict[str, Type[BaseDeploymentProvider]] = {
        "vercel": VercelProvider,
        "oracle": OracleProvider,
        "render": RenderProvider,
        "railway": RailwayProvider,
        "fly": FlyProvider,
        "netlify": NetlifyProvider,
        "neon": NeonProvider,
        "supabase": SupabaseProvider,
        "docker_local": DockerLocalProvider,
    }

    @classmethod
    def get(cls, provider_name: str) -> BaseDeploymentProvider:
        key = provider_name.lower().strip()
        if key not in cls._providers:
            # Fallback mapping
            if "vercel" in key:
                key = "vercel"
            elif "render" in key:
                key = "render"
            elif "railway" in key:
                key = "railway"
            elif "fly" in key:
                key = "fly"
            elif "netlify" in key:
                key = "netlify"
            elif "neon" in key:
                key = "neon"
            elif "supabase" in key:
                key = "supabase"
            elif "docker" in key:
                key = "docker_local"
            else:
                key = "oracle"

        provider_cls = cls._providers[key]
        return provider_cls()

    @classmethod
    def register_provider(cls, slug: str, provider_cls: Type[BaseDeploymentProvider]) -> None:
        cls._providers[slug.lower().strip()] = provider_cls

    @classmethod
    def list_available_providers(cls) -> list[dict[str, Any]]:
        result = []
        for slug in cls._providers:
            inst = cls.get(slug)
            result.append({
                "slug": slug,
                "name": inst.name,
                "provider_type": inst.provider_type
            })
        return result

    @classmethod
    def recommend_provider(cls, framework: str | FrameworkType, has_dockerfile: bool = False) -> dict[str, Any]:
        """Smart provider recommendation scoring engine."""
        if hasattr(framework, "value"):
            fw = str(framework.value).lower()
        else:
            fw = str(framework).lower()

        if has_dockerfile:
            return {
                "recommended_provider": "docker_local",
                "recommended_name": "Docker Local Runtime",
                "score": 98,
                "reason": "Custom Dockerfile detected. Local container engine is recommended for custom runtimes."
            }

        if any(k in fw for k in ["react", "next", "vue", "vite", "angular"]):
            return {
                "recommended_provider": "vercel",
                "recommended_name": "Vercel Cloud",
                "score": 96,
                "reason": "Frontend Javascript framework detected. Vercel provides optimal Global Edge caching and SSR."
            }
        elif any(k in fw for k in ["fastapi", "django", "express", "spring", "flask", "nest", "laravel"]):
            return {
                "recommended_provider": "render",
                "recommended_name": "Render Cloud",
                "score": 94,
                "reason": "Backend web framework detected. Render provides automated web service container management."
            }

        return {
            "recommended_provider": "railway",
            "recommended_name": "Railway Cloud",
            "score": 90,
            "reason": "Multi-language cloud engine recommended."
        }
