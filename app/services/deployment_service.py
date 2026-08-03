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


class DeploymentService:
    """
    Core Deployment Orchestrator service.
    Follows provider abstraction guidelines: uses ProviderFactory to resolve cloud providers
    and never couples directly to Vercel or Oracle Cloud SDKs.
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
        4. Invokes Provider.deploy() via ProviderFactory abstraction
        5. Persists deployment logs and updates status to RUNNING with live URL.
        """
        project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )

        repo = project.repository
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no associated repository"
            )

        # 1. Determine provider slug
        target_provider_slug = (
            provider_name.lower().strip()
            if provider_name
            else cls.determine_default_provider_slug(repo.framework)
        )

        # 2. Get provider instance from ProviderFactory
        try:
            provider_instance = ProviderFactory.get(target_provider_slug)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # 3. Ensure DeploymentProvider DB record exists
        db_provider = db.query(DeploymentProvider).filter(
            DeploymentProvider.slug == target_provider_slug
        ).first()

        if not db_provider:
            db_provider = DeploymentProvider(
                name=provider_instance.name,
                slug=target_provider_slug,
                provider_type=provider_instance.provider_type,
                is_active=True
            )
            db.add(db_provider)
            db.commit()
            db.refresh(db_provider)

        # 4. Create Deployment DB record in QUEUED state
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

        # 5. Log initial Queued status
        log_queued = DeploymentLog(
            deployment_id=deployment.id,
            log_level="INFO",
            message=f"Deployment #{deployment.id} queued for framework '{repo.framework}' targeting provider '{provider_instance.name}'."
        )
        db.add(log_queued)

        # 6. Progress to BUILDING
        deployment.status = DeploymentStatus.BUILDING.value
        log_building = DeploymentLog(
            deployment_id=deployment.id,
            log_level="INFO",
            message=f"Build triggered for repository '{repo.full_name}' on branch '{branch}'."
        )
        db.add(log_building)
        db.commit()

        # 7. Perform deployment via ProviderFactory abstract interface
        env_vars = decrypt_env_vars(project.environment_variables)
        deploy_result = provider_instance.deploy(
            project_name=project.name,
            repo_url=repo.clone_url,
            branch=branch,
            env_vars=env_vars
        )

        # 8. Record provider-generated execution logs
        provider_logs = provider_instance.logs(deploy_result.get("external_deployment_id", ""))
        for msg in provider_logs:
            db.add(DeploymentLog(
                deployment_id=deployment.id,
                log_level="INFO",
                message=msg
            ))

        # 9. Update Deployment final state
        deployment.status = deploy_result.get("status", DeploymentStatus.RUNNING).value
        deployment.live_url = deploy_result.get("live_url")
        db.commit()
        db.refresh(deployment)

        return deployment

    @classmethod
    def get_deployment_logs(cls, db: Session, deployment_id: int, user_id: int) -> list[DeploymentLog]:
        """Fetch logs for a deployment belonging to the user."""
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
