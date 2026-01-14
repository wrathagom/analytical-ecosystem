"""Service discovery and configuration loading."""

import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml


# Category display configuration
CATEGORIES = {
    "database": "Databases",
    "cache": "Cache",
    "search": "Search & Analytics",
    "notebook": "Notebooks",
    "visualization": "Visualization",
    "orchestration": "Orchestration",
    "other": "Other",
}

# Category display order
CATEGORY_ORDER = ["database", "cache", "search", "notebook", "visualization", "orchestration"]


@dataclass
class HealthCheck:
    type: str  # "http" or "exec"
    endpoint: Optional[str] = None
    command: Optional[list] = None


@dataclass
class Service:
    id: str
    name: str
    category: str
    port: Optional[int] = None
    url: Optional[str] = None
    credentials: Optional[str] = None
    depends_on: list = field(default_factory=list)
    startup_time: int = 30
    description: Optional[str] = None
    healthcheck: Optional[HealthCheck] = None
    path: Optional[Path] = None

    @property
    def category_name(self) -> str:
        return CATEGORIES.get(self.category, self.category.title())


def get_project_root() -> Path:
    """Get the project root directory."""
    # Walk up from this file to find the project root
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "docker-compose.yml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")

def load_env_file(path: Path) -> dict[str, str]:
    """Load a simple KEY=VALUE .env file."""
    env: dict[str, str] = {}
    if not path.exists():
        return env

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):]
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        env[key] = value

    return env


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def expand_env_vars(value: str, env: dict[str, str]) -> str:
    """Expand ${VAR} and ${VAR:-default} placeholders."""
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        default = match.group(2)
        resolved = env.get(key)
        if resolved is None or resolved == "":
            return default or ""
        return resolved

    return _ENV_PATTERN.sub(repl, value)


def expand_config(value, env: dict[str, str]):
    """Recursively expand env placeholders in config values."""
    if isinstance(value, dict):
        return {k: expand_config(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_config(v, env) for v in value]
    if isinstance(value, str):
        return expand_env_vars(value, env)
    return value


def discover_services(root: Optional[Path] = None) -> dict[str, Service]:
    """Discover all services from services/*/service.yaml files."""
    if root is None:
        root = get_project_root()

    env = load_env_file(root / ".env")
    env.update(os.environ)

    services_dir = root / "services"
    services = {}

    for service_path in services_dir.iterdir():
        if not service_path.is_dir():
            continue

        config_file = service_path / "service.yaml"
        if not config_file.exists():
            continue

        with open(config_file) as f:
            config = yaml.safe_load(f)

        config = expand_config(config or {}, env)

        service_id = service_path.name

        healthcheck = None
        if "healthcheck" in config:
            hc = config["healthcheck"]
            healthcheck = HealthCheck(
                type=hc.get("type", "http"),
                endpoint=hc.get("endpoint"),
                command=hc.get("command"),
            )

        port = config.get("port")
        if isinstance(port, str):
            try:
                port = int(port.strip())
            except ValueError:
                port = None

        services[service_id] = Service(
            id=service_id,
            name=config.get("name", service_id.title()),
            category=config.get("category", "other"),
            port=port,
            url=config.get("url"),
            credentials=config.get("credentials"),
            depends_on=config.get("depends_on", []),
            startup_time=config.get("startup_time", 30),
            description=config.get("description"),
            healthcheck=healthcheck,
            path=service_path,
        )

    return services


def get_services_by_category(services: dict[str, Service]) -> dict[str, list[Service]]:
    """Group services by category in display order."""
    by_category = {cat: [] for cat in CATEGORY_ORDER}
    by_category["other"] = []

    for service in services.values():
        cat = service.category if service.category in CATEGORY_ORDER else "other"
        by_category[cat].append(service)

    # Sort services within each category by name
    for cat in by_category:
        by_category[cat].sort(key=lambda s: s.name)

    # Remove empty categories
    return {k: v for k, v in by_category.items() if v}
