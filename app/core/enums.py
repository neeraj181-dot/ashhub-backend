from enum import Enum


class DeploymentStatus(str, Enum):
    QUEUED = "Queued"
    BUILDING = "Building"
    DEPLOYING = "Deploying"
    RUNNING = "Running"
    FAILED = "Failed"
    STOPPED = "Stopped"


class FrameworkType(str, Enum):
    REACT = "React"
    NEXTJS = "Next.js"
    VUE = "Vue"
    FASTAPI = "FastAPI"
    DJANGO = "Django"
    NODE_EXPRESS = "Node Express"
    SPRING_BOOT = "Spring Boot"
    UNKNOWN = "Unknown"


class ProviderType(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    BOTH = "both"


class AppType(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
