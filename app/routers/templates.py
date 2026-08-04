from typing import Any, List
from fastapi import APIRouter

router = APIRouter(prefix="/templates", tags=["Starter Templates"])

TEMPLATES_DATA = [
    {
        "id": "react-vite",
        "name": "React + Vite",
        "category": "Frontend",
        "framework": "react",
        "recommended_provider": "vercel",
        "description": "Blazing-fast React single-page web application with Vite bundler.",
        "icon": "Atom",
        "demo_url": "https://react-vite-template.ashhub.dev",
        "build_command": "npm run build",
        "start_command": "npm run preview",
    },
    {
        "id": "nextjs-app",
        "name": "Next.js App Router",
        "category": "Frontend",
        "framework": "nextjs",
        "recommended_provider": "vercel",
        "description": "Full-stack React platform with Server Components, SSR, and API routes.",
        "icon": "Globe",
        "demo_url": "https://nextjs-template.ashhub.dev",
        "build_command": "npm run build",
        "start_command": "npm start",
    },
    {
        "id": "fastapi-server",
        "name": "FastAPI REST API",
        "category": "Backend",
        "framework": "fastapi",
        "recommended_provider": "render",
        "description": "High-performance Python API with OpenAPI docs and SQLAlchemy ORM.",
        "icon": "Zap",
        "demo_url": "https://fastapi-template.ashhub.dev",
        "build_command": "pip install -r requirements.txt",
        "start_command": "uvicorn app.main:app --host 0.0.0.0 --port 10000",
    },
    {
        "id": "django-web",
        "name": "Django Web Platform",
        "category": "Backend",
        "framework": "django",
        "recommended_provider": "render",
        "description": "Batteries-included Python framework with built-in admin console.",
        "icon": "Server",
        "demo_url": "https://django-template.ashhub.dev",
        "build_command": "python manage.py collectstatic --noinput",
        "start_command": "gunicorn config.wsgi:application",
    },
    {
        "id": "node-express",
        "name": "Node.js Express Server",
        "category": "Backend",
        "framework": "node_express",
        "recommended_provider": "render",
        "description": "Minimalist Node.js web framework for modern APIs and microservices.",
        "icon": "Code",
        "demo_url": "https://express-template.ashhub.dev",
        "build_command": "npm install",
        "start_command": "npm start",
    },
    {
        "id": "spring-boot",
        "name": "Spring Boot Microservice",
        "category": "Backend",
        "framework": "spring_boot",
        "recommended_provider": "render",
        "description": "Enterprise Java framework for scalable cloud-native microservices.",
        "icon": "Box",
        "demo_url": "https://springboot-template.ashhub.dev",
        "build_command": "./mvnw clean package",
        "start_command": "java -jar target/*.jar",
    },
]


@router.get("", response_model=List[dict[str, Any]])
def list_starter_templates() -> Any:
    """Retrieve pre-configured starter templates for rapid deployment."""
    return TEMPLATES_DATA
