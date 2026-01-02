"""Service discovery and configuration loading."""

import os
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


def discover_services(root: Optional[Path] = None) -> dict[str, Service]:
    """Discover all services from services/*/service.yaml files."""
    if root is None:
        root = get_project_root()

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

        service_id = service_path.name

        healthcheck = None
        if "healthcheck" in config:
            hc = config["healthcheck"]
            healthcheck = HealthCheck(
                type=hc.get("type", "http"),
                endpoint=hc.get("endpoint"),
                command=hc.get("command"),
            )

        services[service_id] = Service(
            id=service_id,
            name=config.get("name", service_id.title()),
            category=config.get("category", "other"),
            port=config.get("port"),
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
