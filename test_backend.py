import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.core.enums import FrameworkType, DeploymentStatus
from app.services.github_service import GitHubService
from app.services.provider_factory import ProviderFactory
from app.services.providers.base_provider import BaseDeploymentProvider

# Create in-memory SQLite database for testing with StaticPool so memory is shared across test connections
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestAshHubBackend(unittest.TestCase):

    def setUp(self):
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    def test_health_check(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "ok")

    def test_auth_flow(self):
        # 1. Register user
        reg_resp = client.post("/auth/register", json={
            "email": "ash@example.com",
            "password": "SecurePassword123!",
            "full_name": "Ash Ketchum"
        })
        self.assertEqual(reg_resp.status_code, 201, reg_resp.text)
        data = reg_resp.json()
        self.assertEqual(data["user"]["email"], "ash@example.com")
        self.assertIn("token", data)
        token = data["token"]["access_token"]

        # 2. Login user
        login_resp = client.post("/auth/login", json={
            "email": "ash@example.com",
            "password": "SecurePassword123!"
        })
        self.assertEqual(login_resp.status_code, 200)
        login_token = login_resp.json()["token"]["access_token"]

        # 3. Get /auth/me
        me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {login_token}"})
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["email"], "ash@example.com")

    def test_framework_detection(self):
        # React
        self.assertEqual(
            GitHubService.detect_framework(
                files=["package.json"],
                package_json={"dependencies": {"react": "^18.2.0"}}
            ),
            FrameworkType.REACT
        )

        # Next.js
        self.assertEqual(
            GitHubService.detect_framework(
                files=["next.config.js", "package.json"],
                package_json={"dependencies": {"next": "14.0.0", "react": "18.2.0"}}
            ),
            FrameworkType.NEXTJS
        )

        # Vue
        self.assertEqual(
            GitHubService.detect_framework(
                files=["package.json"],
                package_json={"dependencies": {"vue": "^3.3.0"}}
            ),
            FrameworkType.VUE
        )

        # FastAPI
        self.assertEqual(
            GitHubService.detect_framework(
                files=["app/main.py", "requirements.txt"],
                requirements_txt="fastapi==0.109.0\nuvicorn==0.27.0"
            ),
            FrameworkType.FASTAPI
        )

        # Django
        self.assertEqual(
            GitHubService.detect_framework(
                files=["manage.py", "requirements.txt"],
                requirements_txt="django==5.0"
            ),
            FrameworkType.DJANGO
        )

        # Node Express
        self.assertEqual(
            GitHubService.detect_framework(
                files=["package.json"],
                package_json={"dependencies": {"express": "^4.18.2"}}
            ),
            FrameworkType.NODE_EXPRESS
        )

        # Spring Boot
        self.assertEqual(
            GitHubService.detect_framework(
                files=["pom.xml"]
            ),
            FrameworkType.SPRING_BOOT
        )

    def test_provider_factory_and_extensibility(self):
        # 1. Test built-in providers
        vercel = ProviderFactory.get("vercel")
        oracle = ProviderFactory.get("oracle")

        self.assertEqual(vercel.name, "Vercel")
        self.assertEqual(oracle.name, "Oracle Cloud")

        # 2. Test future provider extensibility without modifying core code (e.g. RenderProvider)
        class RenderProvider(BaseDeploymentProvider):
            def __init__(self):
                super().__init__(name="Render", provider_type="both")

            def deploy(self, project_name, repo_url, branch, env_vars, config=None):
                return {
                    "external_deployment_id": f"rnd_{project_name}_001",
                    "status": DeploymentStatus.RUNNING,
                    "live_url": f"https://{project_name}.onrender.com",
                    "message": "Deployed to Render",
                    "provider": self.name
                }

            def status(self, external_deployment_id):
                return DeploymentStatus.RUNNING

            def logs(self, external_deployment_id):
                return ["[Render] Building...", "[Render] Live!"]

            def health_check(self, live_url):
                return {"healthy": True, "url": live_url}

        ProviderFactory.register_provider("render", RenderProvider)
        render_inst = ProviderFactory.get("render")
        self.assertEqual(render_inst.name, "Render")

    def test_full_project_and_deployment_workflow(self):
        # 1. Register & authenticate
        reg_resp = client.post("/auth/register", json={
            "email": "developer@ashhub.io",
            "password": "Password123!"
        })
        token = reg_resp.json()["token"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Connect GitHub & Select Repository
        select_resp = client.post("/github/select", headers=headers, json={
            "github_id": 102,
            "name": "fastapi-backend-api",
            "full_name": "ashhub-org/fastapi-backend-api",
            "clone_url": "https://github.com/ashhub-org/fastapi-backend-api.git",
            "default_branch": "main",
            "framework": FrameworkType.FASTAPI.value
        })
        self.assertEqual(select_resp.status_code, 200)
        repo_id = select_resp.json()["id"]
        self.assertEqual(select_resp.json()["framework"], FrameworkType.FASTAPI.value)

        # 3. Create Project
        proj_resp = client.post("/projects", headers=headers, json={
            "repository_id": repo_id,
            "name": "AshHub Core Backend",
            "description": "Primary backend service for AshHub",
            "env_vars": {"DATABASE_URL": "postgresql://user:pass@host/db", "API_KEY": "secret123"}
        })
        self.assertEqual(proj_resp.status_code, 201)
        proj_id = proj_resp.json()["id"]
        self.assertEqual(proj_resp.json()["env_vars"]["API_KEY"], "secret123")

        # 4. Trigger Deployment (Auto-routes backend FastAPI project to Oracle Cloud)
        deploy_resp = client.post("/deployments", headers=headers, json={
            "project_id": proj_id,
            "branch": "main"
        })
        self.assertEqual(deploy_resp.status_code, 202, deploy_resp.text)
        dep_data = deploy_resp.json()
        dep_id = dep_data["deployment_id"]
        self.assertEqual(dep_data["status"], DeploymentStatus.RUNNING.value)
        self.assertIn("oraclecloud", dep_data["live_url"])

        # 5. Get Deployment Logs
        logs_resp = client.get(f"/deployments/{dep_id}/logs", headers=headers)
        self.assertEqual(logs_resp.status_code, 200)
        logs = logs_resp.json()
        self.assertTrue(len(logs) > 0)
        messages = [l["message"] for l in logs]
        self.assertTrue(any("[OCI]" in m for m in messages))

        # 6. Test Frontend project routing to Vercel
        react_repo = client.post("/github/select", headers=headers, json={
            "name": "react-frontend-app",
            "full_name": "ashhub-org/react-frontend-app",
            "clone_url": "https://github.com/ashhub-org/react-frontend-app.git",
            "default_branch": "main",
            "framework": FrameworkType.REACT.value
        }).json()

        frontend_proj = client.post("/projects", headers=headers, json={
            "repository_id": react_repo["id"],
            "name": "AshHub Web Dashboard"
        }).json()

        fe_deploy = client.post("/deployments", headers=headers, json={
            "project_id": frontend_proj["id"]
        }).json()

        self.assertEqual(fe_deploy["provider_name"], "Vercel")
        self.assertIn("vercel.app", fe_deploy["live_url"])


if __name__ == "__main__":
    unittest.main()
