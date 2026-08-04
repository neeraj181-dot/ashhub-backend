from typing import Any
import httpx
from app.utils.encryption import decrypt_token


class GitHubRepositoryService:
    """Service handling GitHub repository details, branch listing, and contents fetching."""

    @staticmethod
    def list_user_repositories(access_token: str | None = None) -> list[dict[str, Any]]:
        raw_token = decrypt_token(access_token) if access_token else None

        if raw_token and not raw_token.startswith("mock_"):
            headers = {
                "Authorization": f"Bearer {raw_token}",
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
                                "owner": r.get("owner", {}).get("login", "user"),
                                "full_name": r.get("full_name"),
                                "clone_url": r.get("clone_url"),
                                "visibility": "private" if r.get("private") else "public",
                                "private": r.get("private", False),
                                "default_branch": r.get("default_branch", "main"),
                                "language": r.get("language"),
                                "last_updated": r.get("updated_at"),
                                "stars": r.get("stargazers_count", 0)
                            }
                            for r in repos
                        ]
            except Exception:
                pass

        # Return mock repository samples
        return [
            {
                "github_id": 101,
                "name": "react-dashboard-app",
                "owner": "ashhub-org",
                "full_name": "ashhub-org/react-dashboard-app",
                "clone_url": "https://github.com/ashhub-org/react-dashboard-app.git",
                "visibility": "public",
                "private": False,
                "default_branch": "main",
                "language": "TypeScript",
                "last_updated": "2026-08-01T12:00:00Z",
                "stars": 42
            },
            {
                "github_id": 102,
                "name": "fastapi-backend-api",
                "owner": "ashhub-org",
                "full_name": "ashhub-org/fastapi-backend-api",
                "clone_url": "https://github.com/ashhub-org/fastapi-backend-api.git",
                "visibility": "public",
                "private": False,
                "default_branch": "main",
                "language": "Python",
                "last_updated": "2026-08-02T15:30:00Z",
                "stars": 128
            }
        ]

    @staticmethod
    def get_repository(access_token: str | None, owner: str, repo: str) -> dict[str, Any]:
        repos = GitHubRepositoryService.list_user_repositories(access_token)
        for r in repos:
            if r["owner"] == owner and r["name"] == repo:
                return r
        return {
            "github_id": 102,
            "name": repo,
            "owner": owner,
            "full_name": f"{owner}/{repo}",
            "clone_url": f"https://github.com/{owner}/{repo}.git",
            "visibility": "public",
            "private": False,
            "default_branch": "main",
            "language": "TypeScript",
            "last_updated": "2026-08-03T10:00:00Z",
            "stars": 15
        }

    @staticmethod
    def list_branches(access_token: str | None, owner: str, repo: str) -> list[dict[str, Any]]:
        return [
            {"name": "main", "commit_sha": "a1b2c3d4e5f6", "protected": True},
            {"name": "dev", "commit_sha": "9f8e7d6c5b4a", "protected": False}
        ]

    @staticmethod
    def get_contents(access_token: str | None, owner: str, repo: str, path: str = "") -> list[dict[str, Any]]:
        return [
            {"name": "package.json", "path": "package.json", "type": "file", "size": 1024, "download_url": None},
            {"name": "src", "path": "src", "type": "dir", "size": None, "download_url": None}
        ]
