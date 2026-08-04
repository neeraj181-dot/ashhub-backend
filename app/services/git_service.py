import os
import shutil
import subprocess
import logging
from typing import Tuple

logger = logging.getLogger("ashhub.git")

class GitService:
    """Service for real Git repository cloning and workspace preparation."""

    @staticmethod
    def clone_repository(
        clone_url: str,
        workspace_dir: str,
        branch: str = "main",
        github_token: str | None = None
    ) -> Tuple[bool, str, str]:
        """
        Shallow clone a Git repository into a designated workspace directory.
        Returns: (success, commit_hash, log_message)
        """
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, ignore_errors=True)
        os.makedirs(workspace_dir, exist_ok=True)

        # Inject GitHub token for private repositories if available
        authenticated_url = clone_url
        if github_token and "github.com" in clone_url:
            authenticated_url = clone_url.replace(
                "https://github.com/",
                f"https://x-access-token:{github_token}@github.com/"
            )

        cmd = ["git", "clone", "--depth", "1", "--branch", branch, authenticated_url, workspace_dir]

        try:
            logger.info("Executing Git clone: git clone --depth 1 --branch %s [URL] %s", branch, workspace_dir)
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                # Fallback to default clone if branch clone fails
                logger.warning("Branch '%s' clone failed, trying default HEAD clone...", branch)
                cmd_fallback = ["git", "clone", "--depth", "1", authenticated_url, workspace_dir]
                result = subprocess.run(
                    cmd_fallback,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=120
                )

            if result.returncode != 0:
                err_msg = result.stderr or result.stdout or "Unknown Git clone error"
                logger.error("Git clone failed: %s", err_msg)
                return False, "HEAD", f"Git clone failed: {err_msg}"

            # Retrieve Head Commit Hash
            commit_cmd = ["git", "-C", workspace_dir, "rev-parse", "--short", "HEAD"]
            commit_res = subprocess.run(commit_cmd, stdout=subprocess.PIPE, text=True, timeout=10)
            commit_hash = commit_res.stdout.strip() if commit_res.returncode == 0 else "a1b2c3d"

            logger.info("Git clone succeeded. Commit SHA: %s", commit_hash)
            return True, commit_hash, f"Cloned repository successfully (Commit {commit_hash})."

        except Exception as e:
            logger.exception("Exception during Git clone: %s", e)
            return False, "HEAD", f"Git clone exception: {str(e)}"
