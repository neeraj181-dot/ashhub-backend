import logging
import traceback
from typing import Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.enums import DeploymentStatus, FrameworkType
from app.models.project import Project
from app.models.provider import DeploymentProvider
from app.models.deployment import Deployment
from app.models.deployment_log import DeploymentLog
from app.services.provider_factory import ProviderFactory
from app.utils.encryption import decrypt_env_vars

logger = logging.getLogger("ashhub.deployment_service")


class DeploymentService:
    """
    Core Deployment Orchestrator service with explicit trace logging and DB transaction safety.
    Follows provider abstraction guidelines: uses ProviderFactory to resolve cloud providers.
    """

    FRONTEND_FRAMEWORKS = {FrameworkType.REACT, FrameworkType.NEXTJS, FrameworkType.VUE}

    @classmethod
    def determine_default_provider_slug(cls, framework: str) -> str:
        """
        Auto-route frontend applications to Vercel and backend services to Oracle Cloud.
        """
        try:
            fw_enum = FrameworkType(framework)
            if fw_enum in cls.FRONTEND_FRAMEWORKS:
                return "vercel"
        except ValueError:
            pass
        return "oracle"

    @classmethod
    def trigger_deployment(
        cls,
        db: Session,
        user_id: int,
        project_id: int,
        provider_name: str | None = None,
        branch: str = "main",
        commit_hash: str | None = None
    ) -> Deployment:
        """
        Executes the deployment workflow:
        1. Validates project ownership & associated repository framework
        2. Resolves target cloud provider via ProviderFactory
        3. Records Queued/Building state in DB and logs
        4. Delegates execution to ProductionDeploymentEngine
        """
        logger.info("[SERVICE] Entering DeploymentService.trigger_deployment()")
        logger.info("[SERVICE] Project ID: %s, User ID: %s, Target Branch: %s", project_id, user_id, branch)

        # 1. Database Lookup for Project
        try:
            logger.info("[SERVICE] Loading project from database...")
            project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
            if not project:
                logger.warning("[SERVICE ERROR] Project ID=%s for user_id=%s not found", project_id, user_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project with ID {project_id} not found"
                )
            logger.info("[SERVICE] Project found: '%s' (ID=%s)", project.name, project.id)

            repo = project.repository
            if not repo:
                logger.warning("[SERVICE ERROR] Project ID=%s has no associated repository", project_id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Project '{project.name}' has no associated Git repository"
                )
            logger.info("[SERVICE] Repository found: '%s' (Framework=%s)", repo.full_name, repo.framework)

        except HTTPException:
            raise
        except Exception as err:
            db.rollback()
            logger.exception("[SERVICE ERROR] Database lookup exception: %s", err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database query failed: {str(err)}"
            )

        # 2. Determine provider slug
        target_provider_slug = (
            provider_name.lower().strip()
            if provider_name
            else cls.determine_default_provider_slug(repo.framework)
        )
        logger.info("[SERVICE] Resolved target provider slug: '%s'", target_provider_slug)

        # 3. Get provider instance from ProviderFactory
        try:
            logger.info("[SERVICE] Resolving provider via ProviderFactory.get('%s')...", target_provider_slug)
            provider_instance = ProviderFactory.get(target_provider_slug)
            logger.info("[SERVICE] ProviderFactory returned provider: %s (%s)", provider_instance.name, provider_instance.provider_type)
        except Exception as e:
            logger.exception("[SERVICE ERROR] ProviderFactory returned error for '%s': %s", target_provider_slug, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ProviderFactory error: {str(e)}"
            )

        # 4. DB Operation: Ensure DeploymentProvider record exists
        try:
            logger.info("[SERVICE] Checking DeploymentProvider table for slug '%s'...", target_provider_slug)
            db_provider = db.query(DeploymentProvider).filter(
                DeploymentProvider.slug == target_provider_slug
            ).first()

            if not db_provider:
                logger.info("[SERVICE] Creating new DeploymentProvider DB record for '%s'...", target_provider_slug)
                db_provider = DeploymentProvider(
                    name=provider_instance.name,
                    slug=target_provider_slug,
                    provider_type=provider_instance.provider_type,
                    is_active=True
                )
                db.add(db_provider)
                db.commit()
                db.refresh(db_provider)

            logger.info("[SERVICE] DeploymentProvider record ready (ID=%s)", db_provider.id)

            # 5. DB Operation: Create Deployment DB record
            logger.info("[SERVICE] Creating Deployment record in QUEUED state...")
            deployment = Deployment(
                project_id=project.id,
                provider_id=db_provider.id,
                user_id=user_id,
                status=DeploymentStatus.QUEUED.value,
                commit_hash=commit_hash or "a1b2c3d",
                branch=branch,
            )
            db.add(deployment)
            db.commit()
            db.refresh(deployment)
            logger.info("[SERVICE] Created Deployment DB record (ID=%s, Status=%s)", deployment.id, deployment.status)

            # 6. Log initial Queued status
            log_queued = DeploymentLog(
                deployment_id=deployment.id,
                log_level="INFO",
                message=f"Deployment #{deployment.id} queued for framework '{repo.framework}' targeting provider '{provider_instance.name}'."
            )
            db.add(log_queued)
            db.commit()

        except Exception as db_err:
            db.rollback()
            logger.exception("[SERVICE ERROR] Database transaction failure creating deployment: %s", db_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database constraint/transaction failed: {str(db_err)}"
            )

        # 7. Delegate real pipeline execution to ProductionDeploymentEngine
        try:
            logger.info("[SERVICE] Calling ProductionDeploymentEngine.run_deployment_pipeline(db, deployment_id=%s)...", deployment.id)
            from app.services.deployment_engine import ProductionDeploymentEngine
            deployment = ProductionDeploymentEngine.run_deployment_pipeline(db, deployment.id)
            logger.info("[SERVICE] ProductionDeploymentEngine finished cleanly for Deployment ID=%s (Final Status=%s)", deployment.id, deployment.status)
            return deployment
        except Exception as engine_err:
            logger.exception("[SERVICE ERROR] ProductionDeploymentEngine execution error: %s", engine_err)
            db.refresh(deployment)
            return deployment

    @classmethod
    def get_deployment_logs(cls, db: Session, deployment_id: int, user_id: int) -> list[DeploymentLog]:
        """Fetch logs for a deployment belonging to the user."""
        try:
            deployment = db.query(Deployment).filter(
                Deployment.id == deployment_id,
                Deployment.user_id == user_id
            ).first()

            if not deployment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Deployment with ID {deployment_id} not found"
                )

            return db.query(DeploymentLog).filter(
                DeploymentLog.deployment_id == deployment_id
            ).order_by(DeploymentLog.timestamp.asc()).all()
        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
