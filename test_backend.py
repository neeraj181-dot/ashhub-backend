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
        messages = [l["message"] for l in logs]
        self.assertTrue(any("[DEPLOY]" in m or "[OCI]" in m or "[CLONE]" in m for m in messages))

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

    def test_phase10_previews_and_releases(self):
        reg_resp = client.post("/auth/register", json={
            "email": "phase10_tester@ashhub.io",
            "password": "Password123!"
        })
        token = reg_resp.json()["token"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        repo = client.post("/github/select", headers=headers, json={
            "name": "phase10-app",
            "full_name": "ashhub-org/phase10-app",
            "clone_url": "https://github.com/ashhub-org/phase10-app.git",
            "default_branch": "main",
            "framework": FrameworkType.NEXTJS.value
        }).json()

        proj = client.post("/projects", headers=headers, json={
            "repository_id": repo["id"],
            "name": "Phase10 Test Project"
        }).json()
        proj_id = proj["id"]

        # Previews
        prev_resp = client.post(f"/projects/{proj_id}/previews?pr_number=12&branch=feature/auth", headers=headers)
        self.assertEqual(prev_resp.status_code, 200)
        self.assertIn("preview-feature-auth-pr12", prev_resp.json()["preview_url"])

        list_prev = client.get(f"/projects/{proj_id}/previews", headers=headers)
        self.assertEqual(list_prev.status_code, 200)
        self.assertEqual(len(list_prev.json()), 1)

        # Releases
        rel_resp = client.post(f"/projects/{proj_id}/releases?version=v1.5.0&release_notes=Major+release", headers=headers)
        self.assertEqual(rel_resp.status_code, 200)
        self.assertEqual(rel_resp.json()["git_tag"], "v1.5.0")

        list_rel = client.get(f"/projects/{proj_id}/releases", headers=headers)
        self.assertEqual(list_rel.status_code, 200)
        self.assertEqual(len(list_rel.json()), 1)

    def test_phase10_cache_and_queue(self):
        reg_resp = client.post("/auth/register", json={
            "email": "queue_tester@ashhub.io",
            "password": "Password123!"
        })
        token = reg_resp.json()["token"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        repo = client.post("/github/select", headers=headers, json={
            "name": "cache-app",
            "full_name": "ashhub-org/cache-app",
            "clone_url": "https://github.com/ashhub-org/cache-app.git",
            "default_branch": "main",
            "framework": FrameworkType.NEXTJS.value
        }).json()

        proj = client.post("/projects", headers=headers, json={
            "repository_id": repo["id"],
            "name": "Cache Test Project"
        }).json()
        proj_id = proj["id"]

        # Cache stats
        cache_resp = client.get(f"/projects/{proj_id}/cache/stats", headers=headers)
        # Queue status
        queue_resp = client.get("/queue", headers=headers)
        self.assertEqual(queue_resp.status_code, 200)
        self.assertIn("active_workers", queue_resp.json())


    def test_phase11_docker_and_runtime(self):
        # 1. Dockerfile Generator test
        from app.services.docker_generator import DockerfileGenerator
        df_react = DockerfileGenerator.generate_dockerfile(FrameworkType.REACT)
        self.assertIn("nginx:alpine", df_react)

        df_fastapi = DockerfileGenerator.generate_dockerfile(FrameworkType.FASTAPI)
        self.assertIn("uvicorn", df_fastapi)

        # 2. Container exec terminal command test
        from app.services.docker_runtime import DockerRuntimeService
        res = DockerRuntimeService.execute_terminal_command("cnt_test123", "ls -la")
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("Dockerfile", res["output"])

    def test_phase11_secrets_and_recommendation(self):
        # Provider Recommendation test
        rec_fe = ProviderFactory.recommend_provider(FrameworkType.REACT)
        self.assertEqual(rec_fe["recommended_provider"], "vercel")

        rec_be = ProviderFactory.recommend_provider(FrameworkType.FASTAPI)
        self.assertEqual(rec_be["recommended_provider"], "render")

        rec_docker = ProviderFactory.recommend_provider(FrameworkType.FASTAPI, has_dockerfile=True)
        self.assertEqual(rec_docker["recommended_provider"], "docker_local")

    def test_phase12_organizations_and_rbac(self):
        reg_resp = client.post("/auth/register", json={
            "email": "org_owner@ashhub.io",
            "password": "Password123!"
        })
        token = reg_resp.json()["token"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Organization
        org_resp = client.post("/organizations", headers=headers, json={"name": "Acme Enterprise Corp"})
        self.assertEqual(org_resp.status_code, 200)
        self.assertEqual(org_resp.json()["name"], "Acme Enterprise Corp")
        org_id = org_resp.json()["id"]

        # Invite Member
        inv_resp = client.post(f"/organizations/{org_id}/invites", headers=headers, json={
            "email": "developer@acme.com",
            "role": "developer"
        })
        self.assertEqual(inv_resp.status_code, 200)
        self.assertEqual(inv_resp.json()["role"], "developer")

    def test_phase12_api_keys_and_billing(self):
        reg_resp = client.post("/auth/register", json={
            "email": "apikey_user@ashhub.io",
            "password": "Password123!"
        })
        token = reg_resp.json()["token"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create API Key
        key_resp = client.post("/api-keys", headers=headers, json={
            "name": "GitHub Actions Key",
            "scopes": "read,write,deploy"
        })
        self.assertEqual(key_resp.status_code, 200)
        self.assertIn("ash_live_", key_resp.json()["raw_secret"])

        # Admin stats
        admin_resp = client.get("/admin/stats", headers=headers)
        self.assertEqual(admin_resp.status_code, 200)
        self.assertIn("total_users", admin_resp.json())

    def test_phase13_ai_assistant(self):
        reg_resp = client.post("/auth/register", json={
            "email": "ai_user@ashhub.io",
            "password": "Password123!"
        })
        token = reg_resp.json()["token"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. AI Chat
        chat_resp = client.post("/ai/chat", headers=headers, json={"message": "Why did my build fail?"})
        self.assertEqual(chat_resp.status_code, 200)
        self.assertIn("requirements.txt", chat_resp.json()["reply"])


        # 2. Analyze failure
        fail_resp = client.post("/ai/analyze-failure", headers=headers, json={
            "logs": "ModuleNotFoundError: No module named 'fastapi'"
        })
        self.assertEqual(fail_resp.status_code, 200)
        self.assertEqual(fail_resp.json()["issue"], "Missing Dependency Package")

        # 3. Dockerfile Review
        df_resp = client.post("/ai/review-dockerfile", headers=headers, json={
            "dockerfile": "FROM node:18\nCOPY . .\nCMD [\"npm\", \"start\"]"
        })
        self.assertEqual(df_resp.status_code, 200)
        self.assertTrue(len(df_resp.json()["suggestions"]) > 0)

        # 4. Natural language command
        cmd_resp = client.post("/ai/command", headers=headers, json={"command": "deploy my backend"})
        self.assertEqual(cmd_resp.status_code, 200)
        self.assertEqual(cmd_resp.json()["action"], "TRIGGER_DEPLOYMENT")

    def test_import_project_and_github_endpoints(self):
        reg_resp = client.post("/auth/register", json={
            "email": "import_user@ashhub.io",
            "password": "Password123!"
        })
        token = reg_resp.json()["token"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test POST /projects/import -> HTTP 200
        import_resp = client.post("/projects/import", headers=headers, json={
            "owner": "ashhub-org",
            "repo": "react-starter-template",
            "branch": "main",
            "name": "React Starter App"
        })
        self.assertEqual(import_resp.status_code, 200, import_resp.text)
        self.assertEqual(import_resp.json()["name"], "React Starter App")

        # 2. Test GET /github/profile -> HTTP 200
        prof_resp = client.get("/github/profile", headers=headers)
        self.assertEqual(prof_resp.status_code, 200)

        # 3. Test OPTIONS preflight for CORS header verification
        options_resp = client.options("/github/profile", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        self.assertEqual(options_resp.status_code, 200)
        self.assertEqual(options_resp.headers.get("access-control-allow-origin"), "http://localhost:3000")

    def test_production_deployment_engine(self):
        from app.services.build_service import BuildService
        from app.services.git_service import GitService

        # 1. Test BuildService execution
        ok, code, output = BuildService.execute_command("echo AshHub Build Engine Active", cwd=".")
        self.assertTrue(ok)
        self.assertEqual(code, 0)
        self.assertIn("AshHub Build Engine Active", output)

        # 2. Test GitService failure handling gracefully
        ok_git, commit, msg = GitService.clone_repository(
            clone_url="https://github.com/invalid-org/invalid-repo-12345.git",
            workspace_dir="scratch/test_invalid_workspace"
        )
        self.assertFalse(ok_git)
        self.assertIn("failed", msg.lower())

    def test_vercel_provider_rest_api(self):
        from app.services.providers.vercel_provider import VercelProvider

        provider = VercelProvider()
        result = provider.deploy(
            project_name="React Starter App",
            repo_url="https://github.com/ashhub-org/react-starter-template.git",
            branch="main",
            env_vars={"NODE_ENV": "production"}
        )

        self.assertEqual(result["status"].value, "Running")
        self.assertIn("vercel.app", result["live_url"])
        self.assertTrue(result["external_deployment_id"].startswith("vcl_") or result["external_deployment_id"].startswith("dpl_"))

        # Health check verification
        health = provider.health_check(result["live_url"])
        self.assertTrue(health["healthy"])


if __name__ == "__main__":
    unittest.main()







