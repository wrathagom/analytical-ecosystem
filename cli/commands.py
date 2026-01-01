"""CLI command implementations."""

import subprocess
import urllib.request
import urllib.error
from typing import Optional

from .config import Service, discover_services, get_services_by_category, CATEGORIES
from . import docker


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    NC = "\033[0m"  # No Color


def print_color(text: str, color: str = ""):
    """Print colored text."""
    print(f"{color}{text}{Colors.NC}")


def cmd_list():
    """List all available services."""
    services = discover_services()
    by_category = get_services_by_category(services)

    print("Available services:\n")

    for cat_id, cat_services in by_category.items():
        cat_name = CATEGORIES.get(cat_id, cat_id.title())
        print_color(f"  {cat_name}:", Colors.BOLD)
        for svc in cat_services:
            deps = f" (requires: {', '.join(svc.depends_on)})" if svc.depends_on else ""
            print(f"    {svc.id} - {svc.name}{deps}")
        print()


def cmd_start(profiles: list[str]):
    """Start selected services."""
    if not profiles:
        print_color("No services selected. Nothing to start.", Colors.YELLOW)
        return False

    services = discover_services()

    print_color(f"Starting services: {', '.join(profiles)}", Colors.CYAN)
    print()

    if docker.start_services(profiles):
        print()
        print_color("Services started!", Colors.GREEN)
        print()
        print_urls(profiles, services)
        return True
    else:
        print_color("Failed to start services.", Colors.RED)
        return False


def cmd_stop(profiles: list[str]):
    """Stop services."""
    print_color("Stopping services...", Colors.CYAN)

    if docker.stop_services(profiles):
        print_color("Services stopped.", Colors.GREEN)
        return True
    else:
        print_color("Failed to stop services.", Colors.RED)
        return False


def cmd_restart(profiles: list[str]):
    """Restart services."""
    if not profiles:
        print_color("Restarting all running services...", Colors.CYAN)
    else:
        print_color(f"Restarting services: {', '.join(profiles)}", Colors.CYAN)

    if docker.restart_services(profiles):
        print_color("Services restarted.", Colors.GREEN)
        return True
    else:
        print_color("Failed to restart services.", Colors.RED)
        return False


def cmd_status():
    """Show running services."""
    print_color("Running ecosystem services:\n", Colors.CYAN)

    containers = docker.get_running_containers()

    if not containers:
        print_color("No services running.", Colors.YELLOW)
        return

    # Print header
    print(f"{'NAME':<40} {'STATUS':<25} {'PORTS'}")
    print("-" * 80)

    for container in containers:
        name = container["name"].replace("analytical-ecosystem-", "").rstrip("-1")
        print(f"{name:<40} {container['status']:<25} {container['ports']}")


def cmd_logs(profiles: list[str], service: Optional[str] = None):
    """Show service logs."""
    if service:
        print_color(f"Showing logs for: {service}", Colors.CYAN)
    else:
        print_color("Showing logs for all services...", Colors.CYAN)

    docker.get_logs(profiles, service)


def cmd_build(profiles: list[str]):
    """Build service images."""
    if not profiles:
        print_color("Building all service images...", Colors.CYAN)
    else:
        print_color(f"Building images for: {', '.join(profiles)}", Colors.CYAN)

    if docker.build_services(profiles):
        print_color("Build complete.", Colors.GREEN)
        return True
    else:
        print_color("Build failed.", Colors.RED)
        return False


def cmd_clean(profiles: list[str]):
    """Stop services and remove volumes."""
    print_color("WARNING: This will stop all services and remove all volumes!", Colors.RED)
    print_color("All data (databases, logs, etc.) will be permanently deleted.", Colors.RED)
    print()

    confirm = input("Are you sure? (type 'yes' to confirm): ")

    if confirm.lower() == "yes":
        print_color("Stopping services and removing volumes...", Colors.CYAN)
        if docker.clean_services(profiles):
            print_color("Clean complete. All services stopped and volumes removed.", Colors.GREEN)
            return True
        else:
            print_color("Clean failed.", Colors.RED)
            return False
    else:
        print_color("Clean cancelled.", Colors.YELLOW)
        return False


def cmd_nuke(profiles: list[str]):
    """Nuclear clean - remove everything including images."""
    print_color("╔═══════════════════════════════════════════════════════════════╗", Colors.RED)
    print_color("║                    NUCLEAR CLEAN                              ║", Colors.RED + Colors.BOLD)
    print_color("╚═══════════════════════════════════════════════════════════════╝", Colors.RED)
    print()
    print_color("This will PERMANENTLY remove:", Colors.RED)
    print("  • All containers")
    print("  • All volumes (databases, logs, data)")
    print("  • All built images")
    print("  • All networks")
    print()
    print_color("You will need to rebuild everything from scratch.", Colors.YELLOW)
    print()

    confirm = input("Type 'nuke' to confirm: ")

    if confirm.lower() == "nuke":
        print()
        print_color("Nuking everything...", Colors.RED)
        print()
        if docker.nuclear_clean(profiles):
            print_color("Nuclear clean complete. Everything has been removed.", Colors.GREEN)
            return True
        else:
            print_color("Nuclear clean failed.", Colors.RED)
            return False
    else:
        print_color("Cancelled.", Colors.YELLOW)
        return False


def cmd_shell(service: str):
    """Open a shell in a container."""
    if not service:
        # Show available containers
        containers = docker.get_running_containers()
        if not containers:
            print_color("No services running.", Colors.YELLOW)
            return False

        print_color("Available running services:", Colors.YELLOW)
        for c in containers:
            name = c["name"].replace("analytical-ecosystem-", "").rstrip("-1")
            print(f"  {name}")
        print()

        service = input("Enter service name: ").strip()
        if not service:
            print_color("No service specified.", Colors.RED)
            return False

    container_name = f"analytical-ecosystem-{service}-1"

    print_color(f"Opening shell in: {container_name}", Colors.CYAN)
    docker.open_shell(container_name)
    return True


def cmd_test():
    """Run health checks and connection tests."""
    services = discover_services()

    print_color("Running health checks...\n", Colors.CYAN)

    containers = docker.get_running_containers()

    if not containers:
        print_color("No services running.", Colors.YELLOW)
        return False

    all_passed = True

    # Check container health status
    for container in containers:
        name = container["name"]
        service_name = name.replace("analytical-ecosystem-", "").rstrip("-1")

        health = docker.get_container_health(name)
        status = docker.get_container_status(name)

        if health == "healthy":
            print(f"  {Colors.GREEN}✓{Colors.NC} {service_name} - healthy")
        elif health == "unhealthy":
            print(f"  {Colors.RED}✗{Colors.NC} {service_name} - unhealthy")
            all_passed = False
        elif status == "running":
            print(f"  {Colors.YELLOW}~{Colors.NC} {service_name} - running (no healthcheck)")
        else:
            print(f"  {Colors.RED}✗{Colors.NC} {service_name} - {status}")
            all_passed = False

    print()
    print_color("Running connection tests...\n", Colors.CYAN)

    # Run service-specific health checks
    for container in containers:
        name = container["name"]
        service_id = name.replace("analytical-ecosystem-", "").split("-")[0]

        if service_id not in services:
            continue

        service = services[service_id]
        if not service.healthcheck:
            continue

        if service.healthcheck.type == "http" and service.healthcheck.endpoint:
            try:
                req = urllib.request.urlopen(service.healthcheck.endpoint, timeout=5)
                print(f"  {Colors.GREEN}✓{Colors.NC} {service.name} - accepting connections")
            except (urllib.error.URLError, TimeoutError):
                print(f"  {Colors.YELLOW}~{Colors.NC} {service.name} - starting up")

        elif service.healthcheck.type == "exec" and service.healthcheck.command:
            cmd = service.healthcheck.command
            result = docker.exec_in_container(name, cmd)
            if result.returncode == 0:
                print(f"  {Colors.GREEN}✓{Colors.NC} {service.name} - accepting connections")
            else:
                print(f"  {Colors.RED}✗{Colors.NC} {service.name} - not ready")
                all_passed = False

    print()
    if all_passed:
        print_color("All tests passed!", Colors.GREEN)
    else:
        print_color("Some tests failed or services not ready.", Colors.YELLOW)

    return all_passed


def print_urls(profiles: list[str], services: dict[str, Service]):
    """Print access URLs for running services."""
    print_color("Access URLs:", Colors.BOLD)

    for profile in profiles:
        if profile not in services:
            continue

        svc = services[profile]
        if svc.url:
            creds = f" ({svc.credentials})" if svc.credentials else ""
            print(f"  {svc.name}: {svc.url}{creds}")
