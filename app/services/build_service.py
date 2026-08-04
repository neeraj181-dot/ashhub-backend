import os
import subprocess
import logging
from typing import Callable, Tuple

logger = logging.getLogger("ashhub.build")


class BuildService:
    """Service for executing real application build steps."""

    @staticmethod
    def execute_command(
        command: str,
        cwd: str,
        log_callback: Callable[[str], None] | None = None,
        timeout: int = 300
    ) -> Tuple[bool, int, str]:
        """
        Execute a shell command in specified workspace directory.
        Streams stdout and stderr line-by-line via log_callback.
        Returns: (success, exit_code, full_output)
        """
        if not os.path.exists(cwd):
            msg = f"Workspace directory does not exist: {cwd}"
            if log_callback:
                log_callback(f"[ERROR] {msg}")
            return False, 1, msg

        if log_callback:
            log_callback(f"[BUILD] $ {command}")

        logger.info("Executing build command: '%s' in %s", command, cwd)

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            full_logs = []
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    clean_line = line.rstrip()
                    if clean_line:
                        full_logs.append(clean_line)
                        if log_callback:
                            log_callback(f"[BUILD] {clean_line}")

            process.stdout.close()
            return_code = process.wait(timeout=timeout)

            success = return_code == 0
            summary = "\n".join(full_logs)
            if success:
                if log_callback:
                    log_callback(f"[BUILD] Command completed with exit code {return_code}.")
            else:
                if log_callback:
                    log_callback(f"[ERROR] Command failed with exit code {return_code}.")

            return success, return_code, summary

        except Exception as e:
            err_msg = f"Build command execution failed: {str(e)}"
            logger.exception("Build error: %s", err_msg)
            if log_callback:
                log_callback(f"[ERROR] {err_msg}")
            return False, 1, err_msg
