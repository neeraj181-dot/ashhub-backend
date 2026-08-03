import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


class Settings:
    """Application settings and environment variable configurations."""

    PROJECT_NAME: str = "AshHub Backend API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = ""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./ashhub.db"
    )
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY",
        "gK8s-3j3Lw9VpW6B2N7X5c8Y1M0Q4R7T9U2v5X8z1A3="
    )
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "mock_github_client_id")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "mock_github_client_secret")


settings = Settings()
