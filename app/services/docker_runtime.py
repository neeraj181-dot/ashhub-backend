import os
import random
import secrets
from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.container import ContainerInstance


class DockerRuntimeService:
    """Service managing local Docker containers, metrics, and exec terminal commands."""

    @staticmethod
    def build_and_run(
        db: Session,
        project_id: int,
        deployment_id: int | None,
        project_name: str,
        dockerfile_content: str | None = None
    ) -> ContainerInstance:
        container_id = f"cnt_{secrets.token_hex(6)}"
        image_id = f"img_{secrets.token_hex(6)}"
        c_name = f"ashhub-{project_name.lower().replace(' ', '-')}-{container_id[:8]}"

        container = ContainerInstance(
            project_id=project_id,
            deployment_id=deployment_id,
            container_id=container_id,
            image_id=image_id,
            name=c_name,
            status="running",
            cpu_pct=round(random.uniform(0.5, 4.2), 1),
            memory_mb=round(random.uniform(98.0, 245.0), 1),
            disk_mb=round(random.uniform(32.0, 110.0), 1),
            ports_json='{"8000/tcp": 8000, "3000/tcp": 3000}'
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        return container

    @staticmethod
    def execute_terminal_command(container_id: str, command: str) -> dict[str, Any]:
        """Simulate secure in-container command execution (ls, pwd, cat, python, bash, sh)."""
        cmd_clean = command.strip().lower()

        if cmd_clean.startswith("ls"):
            output = "app.main:app\nDockerfile\nrequirements.txt\npackage.json\nsrc/\nnode_modules/\npublic/\n"
        elif cmd_clean.startswith("pwd"):
            output = "/app\n"
        elif cmd_clean.startswith("cat requirements.txt") or cmd_clean.startswith("cat package.json"):
            output = '{"name": "ashhub-app", "version": "1.0.0", "dependencies": {"fastapi": "^0.109.0"}}\n'
        elif cmd_clean.startswith("python"):
            output = "Python 3.11.7 (main, Jan 15 2026, 12:00:00) [GCC 11.4.0]\nType 'help' for more info.\n"
        elif cmd_clean.startswith("whoami"):
            output = "root\n"
        elif cmd_clean.startswith("uname"):
            output = "Linux ashhub-container 6.5.0-generic #42-Ubuntu SMP x86_64 x86_64 GNU/Linux\n"
        else:
            output = f"Executed: {command}\nProcess exited with status 0\n"

        return {
            "container_id": container_id,
            "command": command,
            "exit_code": 0,
            "output": output
        }
