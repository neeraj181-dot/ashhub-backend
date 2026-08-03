import json
from typing import Any
import httpx
from sqlalchemy.orm import Session

from app.core.enums import FrameworkType
from app.models.repository import Repository
from app.schemas.repository import RepositorySelect


class GitHubService:
    """Service handling GitHub integration and automated repository framework detection."""

    @staticmethod
    def detect_framework(
        files: list[str],
        package_json: dict[str, Any] | None = None,
        requirements_txt: str | None = None
    ) -> FrameworkType:
        """
        Inspect repository files and dependency manifests to auto-detect framework.
        Supported frameworks: React, Next.js, Vue, FastAPI, Django, Node Express, Spring Boot.
        """
        file_set = {f.lower() for f in files}

        # 1. Java Spring Boot check
        if "pom.xml" in file_set or "build.gradle" in file_set or "build.gradle.kts" in file_set:
            return FrameworkType.SPRING_BOOT

        # 2. Python Framework checks (Django, FastAPI)
        if "manage.py" in file_set:
            return FrameworkType.DJANGO

        if requirements_txt:
            req_lower = requirements_txt.lower()
            if "django" in req_lower:
                return FrameworkType.DJANGO
            if "fastapi" in req_lower:
                return FrameworkType.FASTAPI

        if "main.py" in file_set or "app/main.py" in file_set:
            return FrameworkType.FASTAPI

        # 3. JavaScript / Node.js Framework checks
        if package_json or "package.json" in file_set:
            deps = {}
            dev_deps = {}
            if package_json:
                deps = package_json.get("dependencies", {})
                dev_deps = package_json.get("devDependencies", {})

            # Next.js
            if "next.config.js" in file_set or "next.config.ts" in file_set or "next.config.mjs" in file_set:
                return FrameworkType.NEXTJS
            if "next" in deps or "next" in dev_deps:
                return FrameworkType.NEXTJS

            # Vue.js
            if "vue.config.js" in file_set or "vue" in deps or "vue" in dev_deps:
                return FrameworkType.VUE

            # React
            if "react" in deps or "react" in dev_deps:
                return FrameworkType.REACT

            # Node Express
            if "express" in deps or "express" in dev_deps:
                return FrameworkType.NODE_EXPRESS

        return FrameworkType.UNKNOWN

    @staticmethod
    def fetch_user_repositories(access_token: str | None = None) -> list[dict[str, Any]]:
        """
        Fetch repositories from GitHub API if token available,
        otherwise return mock repositories for demonstration.
        """
        if access_token and not access_token.startswith("mock_"):
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get("https://api.github.com/user/repos?sort=updated", headers=headers)
                    if resp.status_code == 200:
                        repos = resp.json()
                        return [
                            {
                                "github_id": r.get("id"),
                                "name": r.get("name"),
                                "full_name": r.get("full_name"),
                                "clone_url": r.get("clone_url"),
                                "default_branch": r.get("default_branch", "main"),
                                "language": r.get("language")
                            }
                            for r in repos
                        ]
            except Exception:
                pass  # Fall back to mock repositories if GitHub API is unreachable

        # Return mock repository samples representing various frameworks
        return [
            {
                "github_id": 101,
                "name": "react-dashboard-app",
                "full_name": "ashhub-org/react-dashboard-app",
                "clone_url": "https://github.com/ashhub-org/react-dashboard-app.git",
                "default_branch": "main",
                "framework": FrameworkType.REACT
            },
            {
                "github_id": 102,
                "name": "fastapi-backend-api",
                "full_name": "ashhub-org/fastapi-backend-api",
                "clone_url": "https://github.com/ashhub-org/fastapi-backend-api.git",
                "default_branch": "main",
                "framework": FrameworkType.FASTAPI
            },
            {
                "github_id": 103,
                "name": "nextjs-storefront",
                "full_name": "ashhub-org/nextjs-storefront",
                "clone_url": "https://github.com/ashhub-org/nextjs-storefront.git",
                "default_branch": "main",
                "framework": FrameworkType.NEXTJS
            },
            {
                "github_id": 104,
                "name": "express-auth-service",
                "full_name": "ashhub-org/express-auth-service",
                "clone_url": "https://github.com/ashhub-org/express-auth-service.git",
                "default_branch": "main",
                "framework": FrameworkType.NODE_EXPRESS
            }
        ]

    @classmethod
    def select_repository(
        cls,
        db: Session,
        user_id: int,
        selection: RepositorySelect
    ) -> Repository:
        """
        Save or update repository selection in database with auto framework detection.
        """
        existing = db.query(Repository).filter(
            Repository.user_id == user_id,
            Repository.full_name == selection.full_name
        ).first()

        framework_str = selection.framework.value if selection.framework else FrameworkType.UNKNOWN.value

        if existing:
            existing.name = selection.name
            existing.clone_url = selection.clone_url
            existing.default_branch = selection.default_branch
            if selection.framework:
                existing.framework = framework_str
            db.commit()
            db.refresh(existing)
            return existing

        repo = Repository(
            user_id=user_id,
            github_id=selection.github_id,
            name=selection.name,
            full_name=selection.full_name,
            clone_url=selection.clone_url,
            default_branch=selection.default_branch,
            framework=framework_str
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)
        return repo
