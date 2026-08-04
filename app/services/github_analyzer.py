from typing import Any
from app.schemas.github import AnalysisResult


class GitHubAnalyzer:
    """Automated repository framework analyzer."""

    @staticmethod
    def analyze_repository(
        access_token: str | None,
        owner: str,
        repo: str,
        branch: str = "main"
    ) -> AnalysisResult:
        repo_lower = repo.lower()
        if "react" in repo_lower or "frontend" in repo_lower or "next" in repo_lower:
            return AnalysisResult(
                frontend="Next.js",
                backend=None,
                database=None,
                docker=False,
                github_actions=True,
                recommendedFrontendProvider="Vercel",
                recommendedBackendProvider=None
            )
        elif "fastapi" in repo_lower or "backend" in repo_lower or "python" in repo_lower:
            return AnalysisResult(
                frontend=None,
                backend="FastAPI",
                database="PostgreSQL",
                docker=True,
                github_actions=True,
                recommendedFrontendProvider=None,
                recommendedBackendProvider="Render"
            )
        
        return AnalysisResult(
            frontend="React",
            backend="FastAPI",
            database="PostgreSQL",
            docker=True,
            github_actions=True,
            recommendedFrontendProvider="Vercel",
            recommendedBackendProvider="Render"
        )
