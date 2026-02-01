"""Seed data menu functions for interactive mode."""

import sys
from datetime import datetime, timedelta
from typing import Optional

from ..ui import (
    Colors, clear_screen, print_header, print_color, get_input, wait_for_enter
)
from ..config import discover_services, Service
from .. import docker

from .schemas import SCHEMAS, list_schemas, get_schema
from .generators import create_generator
from .backends import get_backend, get_seedable_backends
from .normalizer import DataNormalizer


# Map service IDs to backend names
SERVICE_TO_BACKEND = {
    "postgres": "postgres",
    "mysql": "mysql",
    "elasticsearch": "elasticsearch",
    "duckdb": "duckdb",
}


def get_seedable_running_services() -> list[dict]:
    """Get running services that can be seeded with data."""
    services = discover_services()
    containers = docker.get_running_containers()
    seedable = []

    seedable_backend_names = get_seedable_backends()

    for container in containers:
        name = container["name"]
        service_id = name.replace("analytical-ecosystem-", "").rsplit("-", 1)[0]

        # Check if this service maps to a seedable backend
        if service_id in SERVICE_TO_BACKEND:
            backend_name = SERVICE_TO_BACKEND[service_id]
            if backend_name in seedable_backend_names:
                health = docker.get_container_health(name)
                service = services.get(service_id)
                seedable.append({
                    "id": service_id,
                    "name": service.name if service else service_id,
                    "backend": backend_name,
                    "health": health,
                })

    return seedable


def select_database() -> Optional[str]:
    """Menu to select database to seed. Returns backend name or None."""
    clear_screen()
    print_header("Seed Data - Select Database")

    seedable = get_seedable_running_services()

    if not seedable:
        print_color("No seedable databases are currently running.", Colors.YELLOW)
        print()
        print("Start one of the following services first:")
        print("  - PostgreSQL (./ecosystem --profiles postgres start)")
        print("  - MySQL (./ecosystem --profiles mysql start)")
        print("  - Elasticsearch (./ecosystem --profiles elasticsearch start)")
        print("  - DuckDB (./ecosystem --profiles duckdb start)")
        wait_for_enter()
        return None

    print_color("Select a database to seed:", Colors.BOLD)
    print()

    for i, svc in enumerate(seedable, 1):
        if svc["health"] == "healthy":
            status = f"{Colors.GREEN}healthy{Colors.NC}"
        elif svc["health"] == "unhealthy":
            status = f"{Colors.RED}unhealthy{Colors.NC}"
        else:
            status = f"{Colors.YELLOW}starting{Colors.NC}"

        print(f"  {Colors.BOLD}{i}{Colors.NC}) {svc['name']} [{status}]")

    print(f"  {Colors.BOLD}b{Colors.NC}) Back")
    print()

    choice = get_input()

    if choice in ("b", "back"):
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(seedable):
            return seedable[idx]["backend"]
    except ValueError:
        pass

    return None


def select_data_type() -> Optional[str]:
    """Menu to select data type to generate. Returns schema name or None."""
    clear_screen()
    print_header("Seed Data - Select Data Type")

    schemas = list_schemas()

    print_color("Select data type:", Colors.BOLD)
    print()

    for i, (name, description) in enumerate(schemas, 1):
        print(f"  {Colors.BOLD}{i}{Colors.NC}) {name.replace('_', ' ').title()} - {description}")

    print(f"  {Colors.BOLD}b{Colors.NC}) Back")
    print()

    choice = get_input()

    if choice in ("b", "back"):
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(schemas):
            return schemas[idx][0]
    except ValueError:
        pass

    return None


def configure_generation(
    backend_name: str,
    schema_name: str,
) -> Optional[dict]:
    """Configure generation parameters. Returns config dict or None."""
    # Default configuration
    config = {
        "count": 1000,
        "start_date": datetime.now() - timedelta(days=365),
        "end_date": datetime.now(),
        "normalize": False,
        "batch_size": 100,
        "clear": False,
    }

    backend = get_backend(backend_name)

    while True:
        clear_screen()
        print_header(f"Seed Data - Configure ({schema_name})")

        print_color("Current configuration:", Colors.BOLD)
        print()
        print(f"  Database:        {backend_name}")
        print(f"  Data type:       {schema_name}")
        print(f"  Record count:    {config['count']}")
        print(f"  Time range:      {config['start_date'].strftime('%Y-%m-%d')} to {config['end_date'].strftime('%Y-%m-%d')}")

        if backend.supports_normalization:
            norm_status = "Yes (normalized)" if config["normalize"] else "No (flat)"
            print(f"  Normalize data:  {norm_status}")
        else:
            print(f"  Normalize data:  {Colors.DIM}Not supported for {backend_name}{Colors.NC}")

        clear_status = f"{Colors.YELLOW}Yes{Colors.NC}" if config["clear"] else "No"
        print(f"  Clear existing:  {clear_status}")

        print()
        print_color("Options:", Colors.BOLD)
        print(f"  {Colors.BOLD}n{Colors.NC}) Change record count")
        print(f"  {Colors.BOLD}s{Colors.NC}) Change start date")
        print(f"  {Colors.BOLD}e{Colors.NC}) Change end date")
        if backend.supports_normalization:
            print(f"  {Colors.BOLD}r{Colors.NC}) Toggle normalization")
        print(f"  {Colors.BOLD}c{Colors.NC}) Toggle clear existing data")
        print(f"  {Colors.BOLD}g{Colors.NC}) Generate data")
        print(f"  {Colors.BOLD}b{Colors.NC}) Back")
        print()

        choice = get_input()

        if choice in ("b", "back"):
            return None

        elif choice == "n":
            print()
            count_str = get_input("Enter record count: ")
            try:
                count = int(count_str)
                if count > 0:
                    config["count"] = count
                else:
                    print_color("Count must be positive.", Colors.RED)
                    wait_for_enter()
            except ValueError:
                print_color("Invalid number.", Colors.RED)
                wait_for_enter()

        elif choice == "s":
            print()
            date_str = get_input("Enter start date (YYYY-MM-DD): ")
            try:
                config["start_date"] = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                print_color("Invalid date format.", Colors.RED)
                wait_for_enter()

        elif choice == "e":
            print()
            date_str = get_input("Enter end date (YYYY-MM-DD): ")
            try:
                config["end_date"] = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                print_color("Invalid date format.", Colors.RED)
                wait_for_enter()

        elif choice == "r" and backend.supports_normalization:
            config["normalize"] = not config["normalize"]

        elif choice == "c":
            config["clear"] = not config["clear"]

        elif choice == "g":
            return config

    return None


def run_generation(
    backend_name: str,
    schema_name: str,
    config: dict,
) -> bool:
    """Run the data generation process. Returns True on success."""
    clear_screen()
    print_header("Seed Data - Generating")

    schema = get_schema(schema_name)
    backend = get_backend(backend_name)
    normalizer = DataNormalizer() if config["normalize"] else None

    count = config["count"]
    batch_size = config["batch_size"]
    normalize = config["normalize"]
    clear = config.get("clear", False)

    print(f"Generating {count} {schema_name} records...")
    print()

    try:
        # Connect to database
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
                    backend.drop_table("customers")
                    backend.drop_table("products_normalized")
            except Exception:
                pass  # Tables might not exist yet

        # Create tables
        if normalize and backend.supports_normalization:
            print_color("Creating normalized tables...", Colors.DIM)
            backend.create_normalized_tables()

        print_color(f"Creating table: {schema.table_name}{'_normalized' if normalize else ''}...", Colors.DIM)
        backend.create_table(schema, normalized=normalize)

        # Create generator
        generator = create_generator(
            schema_name,
            start_date=config["start_date"],
            end_date=config["end_date"],
        )

        # For normalized mode, we need to generate all records first,
        # extract entities, insert them, then insert main records
        if normalize and normalizer:
            print_color("Generating records...", Colors.DIM)
            all_batches = list(generator.generate_batches(count, batch_size))

            # Normalize all records to extract entities
            normalized_batches = []
            for batch in all_batches:
                normalized_batch = [normalizer.normalize_record(r, schema_name) for r in batch]
                normalized_batches.append(normalized_batch)

            # Insert normalized entities FIRST (before main records with foreign keys)
            customers = normalizer.get_customers_table()
            products = normalizer.get_products_table()

            if customers or products:
                print_color("Inserting normalized entities...", Colors.DIM)
                backend.insert_normalized_entities(customers, products)
                if customers:
                    print(f"  Created {len(customers)} unique customers")
                if products:
                    print(f"  Created {len(products)} unique products")
                print()

            # Now insert main records
            print_color("Inserting records...", Colors.DIM)
            total_inserted = 0
            total_batches_count = len(normalized_batches)

            for batch_num, batch in enumerate(normalized_batches, 1):
                inserted = backend.insert_batch(schema, batch, normalized=normalize)
                total_inserted += inserted

                # Progress bar
                progress = batch_num / total_batches_count
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

                # Progress bar
                progress = batch_num / total_batches
                bar_width = 40
                filled = int(bar_width * progress)
                bar = "█" * filled + "░" * (bar_width - filled)
                percent = int(progress * 100)

                sys.stdout.write(f"\r[{bar}] {percent}% ({total_inserted}/{count})")
                sys.stdout.flush()

        print()
        print()

        # Verify count
        table_name = schema.table_name
        if normalize:
            table_name = f"{schema.table_name}_normalized"

        final_count = backend.get_count(table_name)

        print_color(f"✓ Inserted {total_inserted} records into '{table_name}' table", Colors.GREEN)
        print_color(f"  Total records in table: {final_count}", Colors.DIM)

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
        wait_for_enter()
        return True

    except ImportError as e:
        print()
        print_color(f"Missing dependency: {e}", Colors.RED)
        print_color("Install required packages: pip install -r requirements.txt", Colors.YELLOW)
        wait_for_enter()
        return False

    except Exception as e:
        print()
        print_color(f"Error: {e}", Colors.RED)
        wait_for_enter()
        return False


def seed_data_menu():
    """Main entry point for seed data menu."""
    while True:
        # Step 1: Select database
        backend_name = select_database()
        if not backend_name:
            return

        # Step 2: Select data type
        schema_name = select_data_type()
        if not schema_name:
            continue

        # Step 3: Configure
        config = configure_generation(backend_name, schema_name)
        if not config:
            continue

        # Step 4: Generate
        run_generation(backend_name, schema_name, config)
        return
