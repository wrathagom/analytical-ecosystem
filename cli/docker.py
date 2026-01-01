"""Docker Compose wrapper functions."""

import subprocess
import os
from pathlib import Path
from typing import Optional

from .config import get_project_root, Service


PROJECT_NAME = "analytical-ecosystem"


def get_compose_dir() -> Path:
    """Get the docker-compose directory."""
    return get_project_root() / "orchestration" / "docker"


def get_env_file() -> Path:
    """Get the .env file path."""
    return get_project_root() / ".env"


def ensure_env():
    """Ensure .env file exists with required variables."""
    env_file = get_env_file()
    if not env_file.exists():
        uid = os.getuid()
        env_file.write_text(f"AIRFLOW_UID={uid}\n")


def build_profile_args(profiles: list[str]) -> list[str]:
    """Build --profile arguments for docker compose."""
    args = []
    for profile in profiles:
        args.extend(["--profile", profile])
    return args


def compose_command(
    cmd: list[str],
    profiles: Optional[list[str]] = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """Run a docker compose command."""
    compose_dir = get_compose_dir()

    full_cmd = ["docker", "compose"]

    if profiles:
        full_cmd.extend(build_profile_args(profiles))

    full_cmd.extend(cmd)

    return subprocess.run(
        full_cmd,
        cwd=compose_dir,
        capture_output=capture_output,
        text=True,
    )


def start_services(profiles: list[str], build: bool = True) -> bool:
    """Start services with the given profiles."""
    ensure_env()

    cmd = ["up", "-d"]
    if build:
        cmd.append("--build")

    result = compose_command(cmd, profiles)
    return result.returncode == 0


def stop_services(profiles: list[str]) -> bool:
    """Stop services."""
    result = compose_command(["down"], profiles)
    return result.returncode == 0


def restart_services(profiles: list[str]) -> bool:
    """Restart services."""
    result = compose_command(["restart"], profiles)
    return result.returncode == 0


def build_services(profiles: list[str]) -> bool:
    """Build service images."""
    result = compose_command(["build"], profiles)
    return result.returncode == 0


def clean_services(profiles: list[str]) -> bool:
    """Stop services and remove volumes."""
    result = compose_command(["down", "-v"], profiles)
    return result.returncode == 0


def nuclear_clean(profiles: list[str]) -> bool:
    """Complete reset - remove containers, volumes, images, networks."""
    compose_dir = get_compose_dir()

    # Stop and remove everything including images
    result = compose_command(["down", "-v", "--rmi", "all", "--remove-orphans"], profiles)

    # Also remove any dangling volumes with our project name
    subprocess.run(
        ["docker", "volume", "ls", "-q", "-f", "name=analytical-ecosystem"],
        capture_output=True,
        text=True,
    )

    # Remove the network if it exists
    subprocess.run(
        ["docker", "network", "rm", "analytical-ecosystem"],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def get_logs(profiles: list[str], service: Optional[str] = None, follow: bool = True):
    """Show logs for services."""
    cmd = ["logs"]
    if follow:
        cmd.append("-f")
    if service:
        cmd.append(service)

    compose_command(cmd, profiles)


def get_running_containers() -> list[dict]:
    """Get list of running containers in the ecosystem."""
    # Try by project label first
    result = subprocess.run(
        [
            "docker", "ps",
            "--filter", f"label=com.docker.compose.project={PROJECT_NAME}",
            "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"
        ],
        capture_output=True,
        text=True,
    )

    containers = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        containers.append({
            "name": parts[0],
            "status": parts[1] if len(parts) > 1 else "",
            "ports": parts[2] if len(parts) > 2 else "",
        })

    # Also check by network if no results from label
    if not containers:
        result = subprocess.run(
            [
                "docker", "ps",
                "--filter", f"network={PROJECT_NAME}",
                "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"
            ],
            capture_output=True,
            text=True,
        )

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            containers.append({
                "name": parts[0],
                "status": parts[1] if len(parts) > 1 else "",
                "ports": parts[2] if len(parts) > 2 else "",
            })

    return containers


def get_container_health(container_name: str) -> str:
    """Get health status of a container."""
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "none"


def get_container_status(container_name: str) -> str:
    """Get status of a container."""
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "not found"
    return result.stdout.strip()


def exec_in_container(container_name: str, command: list[str]) -> subprocess.CompletedProcess:
    """Execute a command in a container."""
    return subprocess.run(
        ["docker", "exec", container_name] + command,
        capture_output=True,
        text=True,
    )


def open_shell(container_name: str):
    """Open an interactive shell in a container."""
    # Try bash first, fall back to sh
    result = subprocess.run(
        ["docker", "exec", "-it", container_name, "/bin/bash"],
    )
    if result.returncode != 0:
        subprocess.run(
            ["docker", "exec", "-it", container_name, "/bin/sh"],
        )
