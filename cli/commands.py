"""CLI command implementations."""

import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from .config import Service, discover_services, get_services_by_category, CATEGORIES, get_project_root
from . import docker
from . import env as env_utils


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    NC = "\033[0m"  # No Color


def print_color(text: str, color: str = ""):
    """Print colored text."""
    print(f"{color}{text}{Colors.NC}")


CONTAINER_PREFIX = "analytical-ecosystem-"


def container_to_service_id(container_name: str) -> str:
    """Extract service id from a compose container name."""
    name = container_name
    if name.startswith(CONTAINER_PREFIX):
        name = name[len(CONTAINER_PREFIX):]
    if "-" in name:
        return name.rsplit("-", 1)[0]
    return name


def print_service_warnings(
    services: dict[str, Service],
    profiles: Optional[list[str]] = None,
) -> None:
    """Print validation warnings for selected services."""
    selected = profiles or list(services.keys())
    warnings: list[str] = []

    for service_id in selected:
        service = services.get(service_id)
        if not service or not service.warnings:
            continue
        for warning in service.warnings:
            warnings.append(f"{service_id}: {warning}")

    if warnings:
        print_color("Service config warnings:", Colors.YELLOW)
        for warning in warnings:
            print(f"  - {warning}")
        print()


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

    print_service_warnings(services)


def cmd_start(profiles: list[str]):
    """Start selected services."""
    if not profiles:
        print_color("No services selected. Nothing to start.", Colors.YELLOW)
        return False

    services = discover_services()
    print_service_warnings(services, profiles)

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
        name = container_to_service_id(container["name"])
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
            name = container_to_service_id(c["name"])
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
        service_id = container_to_service_id(name)

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


def cmd_env(profiles: list[str], output: str) -> bool:
    """Generate a consolidated env file from fragments."""
    root = get_project_root()
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path

    try:
        selected, fragments = env_utils.generate_env_file(
            profiles,
            output_path=output_path,
            root=root,
        )
    except ValueError as exc:
        print_color(str(exc), Colors.RED)
        return False

    print_color(f"Wrote {output_path}", Colors.GREEN)
    if fragments:
        print_color("Included fragments:", Colors.CYAN)
        for fragment in fragments:
            print(f"  {fragment.relative_to(root)}")
    else:
        print_color("No env fragments found.", Colors.YELLOW)
    return True


def cmd_seed(args) -> bool:
    """Seed database with fake data."""
    from .seed import get_backend, get_schema, create_generator, list_schemas
    from .seed.normalizer import DataNormalizer

    db = args.db
    data_type = args.type
    count = args.count
    batch_size = args.batch_size
    normalize = args.normalize
    clear = getattr(args, 'clear', False)

    # Parse dates
    if args.start:
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d")
        except ValueError:
            print_color(f"Invalid start date format: {args.start}. Use YYYY-MM-DD.", Colors.RED)
            return False
    else:
        start_date = datetime.now() - timedelta(days=365)

    if args.end:
        try:
            end_date = datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            print_color(f"Invalid end date format: {args.end}. Use YYYY-MM-DD.", Colors.RED)
            return False
    else:
        end_date = datetime.now()

    # Validate data type
    valid_types = [name for name, _ in list_schemas()]
    if data_type not in valid_types:
        print_color(f"Invalid data type: {data_type}", Colors.RED)
        print(f"Available types: {', '.join(valid_types)}")
        return False

    # Get backend and schema
    try:
        backend = get_backend(db)
        schema = get_schema(data_type)
    except ValueError as e:
        print_color(str(e), Colors.RED)
        return False

    # Check normalization support
    if normalize and not backend.supports_normalization:
        print_color(f"Normalization not supported for {db}. Using flat mode.", Colors.YELLOW)
        normalize = False

    normalizer = DataNormalizer() if normalize else None

    print_color(f"Seeding {db} with {count} {data_type} records...", Colors.CYAN)
    print(f"  Time range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"  Normalize: {normalize}")
    if clear:
        print(f"  Clear existing: Yes")
    print()

    try:
        # Connect
        backend.connect()

        # Clear existing data if requested
        if clear:
            table_name = schema.table_name
            if normalize:
                table_name = f"{schema.table_name}_normalized"
            print_color(f"Clearing existing data from {table_name}...", Colors.YELLOW)
            try:
                backend.drop_table(table_name)
                if normalize:
                    # Also clear normalized entity tables if they exist
                    backend.drop_table("customers")
                    backend.drop_table("products_normalized")
            except Exception:
                pass  # Tables might not exist yet

        # Create tables
        if normalize:
            backend.create_normalized_tables()

        backend.create_table(schema, normalized=normalize)

        # Generate data
        generator = create_generator(data_type, start_date, end_date)

        # For normalized mode, we need to generate all records first,
        # extract entities, insert them, then insert main records
        if normalize and normalizer:
            print("Generating records...")
            all_batches = list(generator.generate_batches(count, batch_size))

            # Normalize all records to extract entities
            normalized_batches = []
            for batch in all_batches:
                normalized_batch = [normalizer.normalize_record(r, data_type) for r in batch]
                normalized_batches.append(normalized_batch)

            # Insert normalized entities FIRST (before main records with foreign keys)
            customers = normalizer.get_customers_table()
            products = normalizer.get_products_table()

            if customers or products:
                print("Inserting normalized entities...")
                backend.insert_normalized_entities(customers, products)
                if customers:
                    print(f"  Created {len(customers)} unique customers")
                if products:
                    print(f"  Created {len(products)} unique products")
                print()

            # Now insert main records
            total_inserted = 0
            total_batches = len(normalized_batches)

            for batch_num, batch in enumerate(normalized_batches, 1):
                inserted = backend.insert_batch(schema, batch, normalized=normalize)
                total_inserted += inserted

                # Progress
                progress = batch_num / total_batches
                bar_width = 40
                filled = int(bar_width * progress)
                bar = "█" * filled + "░" * (bar_width - filled)
                percent = int(progress * 100)

                sys.stdout.write(f"\r[{bar}] {percent}% ({total_inserted}/{count})")
                sys.stdout.flush()
        else:
            # Non-normalized mode: generate and insert in batches
            total_inserted = 0
            batch_num = 0
            total_batches = (count + batch_size - 1) // batch_size

            for batch in generator.generate_batches(count, batch_size):
                batch_num += 1

                inserted = backend.insert_batch(schema, batch, normalized=False)
                total_inserted += inserted

                # Progress
                progress = batch_num / total_batches
                bar_width = 40
                filled = int(bar_width * progress)
                bar = "█" * filled + "░" * (bar_width - filled)
                percent = int(progress * 100)

                sys.stdout.write(f"\r[{bar}] {percent}% ({total_inserted}/{count})")
                sys.stdout.flush()

        print()
        print()

        # Final count
        table_name = schema.table_name
        if normalize:
            table_name = f"{schema.table_name}_normalized"

        final_count = backend.get_count(table_name)

        print_color(f"✓ Inserted {total_inserted} records into '{table_name}'", Colors.GREEN)
        print(f"  Total records in table: {final_count}")

        # Display connection info
        conn_info = backend.get_connection_info()
        if conn_info:
            print()
            print_color("Connection info:", Colors.CYAN)
            if "database" in conn_info:
                print(f"  Database: {conn_info['database']}")
            if "host" in conn_info:
                print(f"  Host: {conn_info['host']}:{conn_info['port']}")
            if "user" in conn_info:
                print(f"  User: {conn_info['user']}")
            if "password" in conn_info:
                print(f"  Password: {conn_info['password']}")
            if "url" in conn_info:
                print(f"  URL: {conn_info['url']}")
            if "connect_cmd" in conn_info:
                print()
                print_color("Connect with:", Colors.DIM)
                print(f"  {conn_info['connect_cmd']}")

        backend.disconnect()
        return True

    except ImportError as e:
        print_color(f"Missing dependency: {e}", Colors.RED)
        print_color("Install required packages: pip install -r requirements.txt", Colors.YELLOW)
        return False

    except Exception as e:
        print_color(f"Error: {e}", Colors.RED)
        return False
