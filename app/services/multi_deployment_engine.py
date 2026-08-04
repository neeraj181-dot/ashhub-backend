import logging
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.models.deployment import Deployment
from app.models.project import Project
from app.services.provider_factory import ProviderFactory
from app.services.deployment_engine import ProductionDeploymentEngine
from app.core.enums import DeploymentStatus

logger = logging.getLogger("ashhub.multi_deployment_engine")


class MultiDeploymentEngine:
    """
    Multi-Component Deployment Orchestrator.
    Deploys Frontend, Backend, Database, and Storage components independently or together.
    """

    @classmethod
    def execute_plan(
        cls,
        db: Session,
        user_id: int,
        project_id: int,
        plan: Dict[str, Any],
        scope: str = "EVERYTHING"  # 'EVERYTHING', 'FRONTEND', 'BACKEND', 'DATABASE'
    ) -> Dict[str, Any]:
        """
        Executes multi-component deployment according to selected plan and scope.
        """
        logger.info("[MULTI ENGINE] Executing deployment plan for project_id=%s, scope=%s", project_id, scope)

        project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
        if not project:
            raise ValueError(f"Project #{project_id} not found")

        results = {}

        # 1. Deploy Database if included in scope
        if scope in ("EVERYTHING", "DATABASE") and plan.get("database_provider") and plan.get("database_provider") != "skip":
            db_provider_slug = plan.get("database_provider", "neon")
            logger.info("[MULTI ENGINE] Triggering Database deployment targeting '%s'...", db_provider_slug)
            try:
                db_provider = ProviderFactory.get(db_provider_slug)
                db_res = db_provider.deploy(
                    project_name=f"{project.name} DB",
                    repo_url=project.repository.clone_url if project.repository else "",
                    branch="main",
                    env_vars={}
                )
                results["database"] = {
                    "component": "Database",
                    "provider": db_provider.name,
                    "status": "Running",
                    "url": db_res.get("live_url"),
                    "connection_string": db_res.get("connection_string"),
                    "message": db_res.get("message")
                }
            except Exception as db_err:
                logger.warning("[MULTI ENGINE] Database deployment notice: %s", db_err)
                results["database"] = {"component": "Database", "provider": db_provider_slug, "status": "Failed", "error": str(db_err)}

        # 2. Deploy Backend if included in scope
        if scope in ("EVERYTHING", "BACKEND") and plan.get("backend_provider") and plan.get("backend_provider") != "skip":
            backend_provider_slug = plan.get("backend_provider", "render")
            logger.info("[MULTI ENGINE] Triggering Backend deployment targeting '%s'...", backend_provider_slug)
            try:
                backend_provider = ProviderFactory.get(backend_provider_slug)
                be_res = backend_provider.deploy(
                    project_name=f"{project.name} Backend",
                    repo_url=project.repository.clone_url if project.repository else "",
                    branch="main",
                    env_vars=project.env_vars or {}
                )
                results["backend"] = {
                    "component": "Backend",
                    "provider": backend_provider.name,
                    "status": "Running",
                    "url": be_res.get("live_url"),
                    "message": be_res.get("message")
                }
            except Exception as be_err:
                logger.warning("[MULTI ENGINE] Backend deployment notice: %s", be_err)
                results["backend"] = {"component": "Backend", "provider": backend_provider_slug, "status": "Failed", "error": str(be_err)}

        # 3. Deploy Frontend if included in scope
        if scope in ("EVERYTHING", "FRONTEND") and plan.get("frontend_provider") and plan.get("frontend_provider") != "skip":
            frontend_provider_slug = plan.get("frontend_provider", "vercel")
            logger.info("[MULTI ENGINE] Triggering Frontend deployment targeting '%s'...", frontend_provider_slug)
            try:
                frontend_provider = ProviderFactory.get(frontend_provider_slug)
                fe_res = frontend_provider.deploy(
                    project_name=f"{project.name} Frontend",
                    repo_url=project.repository.clone_url if project.repository else "",
                    branch="main",
                    env_vars=project.env_vars or {}
                )
                results["frontend"] = {
                    "component": "Frontend",
                    "provider": frontend_provider.name,
                    "status": "Running",
                    "url": fe_res.get("live_url"),
                    "message": fe_res.get("message")
                }
            except Exception as fe_err:
                logger.warning("[MULTI ENGINE] Frontend deployment notice: %s", fe_err)
                results["frontend"] = {"component": "Frontend", "provider": frontend_provider_slug, "status": "Failed", "error": str(fe_err)}

        logger.info("[MULTI ENGINE] Multi-component deployment complete. Results: %s", results)
        return {
            "status": "success",
            "project_id": project.id,
            "project_name": project.name,
            "scope": scope,
            "components": results
        }
