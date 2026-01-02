"""Interactive UI for service selection."""

import os
import sys
import webbrowser
from typing import Optional

from .config import discover_services, get_services_by_category, CATEGORIES, Service
from . import docker


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    NC = "\033[0m"


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def print_color(text: str, color: str = ""):
    """Print colored text."""
    print(f"{color}{text}{Colors.NC}")


def print_header(subtitle: str = ""):
    """Print the header banner."""
    print_color("╔═══════════════════════════════════════════════════════════════╗", Colors.CYAN)
    print_color("║               Analytical Ecosystem                            ║", Colors.CYAN + Colors.BOLD)
    print_color("╚═══════════════════════════════════════════════════════════════╝", Colors.CYAN)
    if subtitle:
        print_color(f"\n{subtitle}", Colors.DIM)
    print()


def get_input(prompt: str = "> ") -> str:
    """Get user input with error handling."""
    try:
        return input(f"{Colors.BOLD}{prompt}{Colors.NC}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        sys.exit(0)


def wait_for_enter():
    """Wait for user to press Enter."""
    input(f"\n{Colors.DIM}Press Enter to continue...{Colors.NC}")


def get_running_services(services: dict[str, Service]) -> list[dict]:
    """Get list of running services with their details."""
    containers = docker.get_running_containers()
    running = []

    for container in containers:
        name = container["name"]
        # Extract service id from container name (analytical-ecosystem-{service}-1)
        service_id = name.replace("analytical-ecosystem-", "").rsplit("-", 1)[0]

        health = docker.get_container_health(name)

        service = services.get(service_id)
        if service:
            running.append({
                "id": service_id,
                "name": service.name,
                "health": health,
                "url": service.url,
                "credentials": service.credentials,
                "container": name,
            })

    return running


def print_running_services(running: list[dict]):
    """Display currently running services."""
    print_color("Running services:", Colors.BOLD)
    print()

    for svc in running:
        if svc["health"] == "healthy":
            icon = f"{Colors.GREEN}✓{Colors.NC}"
            status = f"{Colors.GREEN}healthy{Colors.NC}"
        elif svc["health"] == "unhealthy":
            icon = f"{Colors.RED}✗{Colors.NC}"
            status = f"{Colors.RED}unhealthy{Colors.NC}"
        else:
            icon = f"{Colors.YELLOW}~{Colors.NC}"
            status = f"{Colors.YELLOW}starting{Colors.NC}"

        url_info = ""
        if svc["url"]:
            creds = f" ({svc['credentials']})" if svc["credentials"] else ""
            url_info = f" → {svc['url']}{creds}"

        print(f"  {icon} {svc['name']} [{status}]{url_info}")

    print()


# =============================================================================
# MAIN MENU - NO SERVICES RUNNING
# =============================================================================

def menu_no_services(services: dict[str, Service], all_profiles: list[str]) -> bool:
    """Menu when no services are running. Returns False to exit."""
    clear_screen()
    print_header()

    print_color("No services currently running.", Colors.YELLOW)
    print()
    print_color("What would you like to do?", Colors.BOLD)
    print()
    print(f"  {Colors.BOLD}1{Colors.NC}) Start services")
    print(f"  {Colors.BOLD}2{Colors.NC}) Build images")
    print(f"  {Colors.BOLD}3{Colors.NC}) Nuclear clean (remove everything)")
    print(f"  {Colors.BOLD}q{Colors.NC}) Quit")
    print()

    choice = get_input()

    if choice in ("q", "quit", "exit"):
        print("Goodbye!")
        return False

    elif choice == "1":
        handle_service_selection(services)

    elif choice == "2":
        print()
        print_color("Building all service images...", Colors.CYAN)
        docker.build_services(all_profiles)
        print_color("Build complete.", Colors.GREEN)
        wait_for_enter()

    elif choice == "3":
        nuclear_clean_prompt(all_profiles)

    return True


def handle_service_selection(services: dict[str, Service]):
    """Handle the service selection and action flow."""
    current_selection: set[str] = set()

    while True:
        selected, action, current_selection = service_selector(services, current_selection)

        if action == "edit":
            # User wants to edit selection, loop back with current selection
            continue

        elif action == "start" and selected:
            print()
            print_color(f"Starting: {', '.join(sorted(selected))}", Colors.CYAN)
            print()
            docker.start_services(selected)
            print()
            print_color("Services started!", Colors.GREEN)
            wait_for_enter()
            break

        elif action == "build" and selected:
            print()
            print_color(f"Building: {', '.join(sorted(selected))}", Colors.CYAN)
            print()
            docker.build_services(selected)
            print()
            print_color("Build complete!", Colors.GREEN)
            wait_for_enter()
            break

        else:
            # Cancelled or back
            break


# =============================================================================
# MAIN MENU - SERVICES RUNNING
# =============================================================================

def menu_services_running(
    services: dict[str, Service],
    all_profiles: list[str],
    running: list[dict]
) -> bool:
    """Menu when services are running. Returns False to exit."""
    clear_screen()
    print_header()

    print_running_services(running)

    print_color("What would you like to do?", Colors.BOLD)
    print()
    print(f"  {Colors.BOLD}1{Colors.NC}) Open in browser")
    print(f"  {Colors.BOLD}2{Colors.NC}) View logs")
    print(f"  {Colors.BOLD}3{Colors.NC}) Open shell")
    print(f"  {Colors.BOLD}4{Colors.NC}) Run health checks")
    print(f"  {Colors.BOLD}5{Colors.NC}) Start more services")
    print(f"  {Colors.BOLD}6{Colors.NC}) Rebuild services")
    print(f"  {Colors.BOLD}7{Colors.NC}) Restart services")
    print(f"  {Colors.BOLD}8{Colors.NC}) Stop services")
    print(f"  {Colors.BOLD}q{Colors.NC}) Quit")
    print()

    choice = get_input()

    if choice in ("q", "quit", "exit"):
        print("Goodbye!")
        return False

    elif choice == "1":
        open_browser_menu(running, services)

    elif choice == "2":
        view_logs_menu(running, all_profiles)

    elif choice == "3":
        shell_menu(running)

    elif choice == "4":
        run_health_checks(services, running)
        wait_for_enter()

    elif choice == "5":
        # Filter out already running services
        running_ids = {r["id"] for r in running}
        available = {k: v for k, v in services.items() if k not in running_ids}

        if not available:
            print_color("\nAll services are already running.", Colors.YELLOW)
            wait_for_enter()
        else:
            handle_service_selection(available)

    elif choice == "6":
        rebuild_menu(running, all_profiles)

    elif choice == "7":
        restart_menu(running, all_profiles)

    elif choice == "8":
        stop_menu(running, all_profiles)

    return True


# =============================================================================
# SERVICE SELECTOR
# =============================================================================

def service_selector(
    services: dict[str, Service],
    initial_selection: set[str] = None
) -> tuple[list[str], str, set[str]]:
    """
    Interactive service selector.
    Returns (selected_profiles, action, current_selection).
    action is 'start', 'build', 'edit', or '' if cancelled.
    """
    by_category = get_services_by_category(services)
    selected: set[str] = set(initial_selection) if initial_selection else set()
    idx_to_profile: dict[int, str] = {}

    while True:
        clear_screen()
        print_header("Select services")

        # Build index and display
        idx = 1
        idx_to_profile.clear()

        for cat_id, cat_services in by_category.items():
            cat_name = CATEGORIES.get(cat_id, cat_id.title())
            print_color(f"── {cat_name} ──", Colors.BLUE + Colors.BOLD)

            for svc in cat_services:
                idx_to_profile[idx] = svc.id

                checkbox = f"{Colors.GREEN}[✓]{Colors.NC}" if svc.id in selected else "[ ]"
                deps = ""
                if svc.depends_on:
                    deps = f" {Colors.DIM}(requires: {', '.join(svc.depends_on)}){Colors.NC}"

                print(f"  {checkbox} {Colors.BOLD}{idx}{Colors.NC}) {svc.name}{deps}")
                idx += 1
            print()

        # Show selection status
        if selected:
            print_color(f"Selected: {', '.join(sorted(selected))}", Colors.GREEN)
        else:
            print_color("No services selected", Colors.DIM)

        print()
        print(f"  {Colors.DIM}Enter numbers to toggle (e.g., 1 3 5){Colors.NC}")
        print(f"  {Colors.DIM}[a]ll  [n]one  [d]one  [b]ack{Colors.NC}")
        print()

        choice = get_input()

        if choice in ("b", "back"):
            return [], "", selected

        elif choice in ("d", "done"):
            if selected:
                return selected_action_menu(list(selected), services, selected)
            else:
                print_color("\nNo services selected.", Colors.YELLOW)
                wait_for_enter()

        elif choice in ("a", "all"):
            selected = set(services.keys())

        elif choice in ("n", "none"):
            selected.clear()

        else:
            # Parse numbers
            nums = choice.replace(",", " ").split()
            for num in nums:
                try:
                    n = int(num)
                    if n in idx_to_profile:
                        profile = idx_to_profile[n]
                        if profile in selected:
                            selected.remove(profile)
                        else:
                            selected.add(profile)
                except ValueError:
                    pass


def selected_action_menu(
    selected: list[str],
    services: dict[str, Service],
    selection_set: set[str]
) -> tuple[list[str], str, set[str]]:
    """Show action menu for selected services. Returns (profiles, action, selection_set)."""
    while True:
        clear_screen()
        print_header("Selected services")

        # Show selected services
        print_color("You have selected:", Colors.BOLD)
        print()
        for svc_id in sorted(selected):
            svc = services.get(svc_id)
            if svc:
                url_info = f" → {svc.url}" if svc.url else ""
                print(f"  • {svc.name}{url_info}")
        print()

        print_color("What would you like to do?", Colors.BOLD)
        print()
        print(f"  {Colors.BOLD}1{Colors.NC}) Start services")
        print(f"  {Colors.BOLD}2{Colors.NC}) Build images")
        print(f"  {Colors.BOLD}e{Colors.NC}) Edit selection")
        print(f"  {Colors.BOLD}b{Colors.NC}) Back to main menu")
        print()

        choice = get_input()

        if choice in ("b", "back"):
            return [], "", selection_set

        elif choice in ("e", "edit"):
            # Return to selector with current selection
            return [], "edit", selection_set

        elif choice == "1":
            return selected, "start", selection_set

        elif choice == "2":
            return selected, "build", selection_set


# =============================================================================
# SUB-MENUS
# =============================================================================

def open_browser_menu(running: list[dict], services: dict[str, Service]):
    """Menu to open a service in the browser."""
    clear_screen()
    print_header("Open in browser")

    # Filter to only services with URLs
    web_services = [r for r in running if r.get("url") and r["url"].startswith("http")]

    if not web_services:
        print_color("No web services currently running.", Colors.YELLOW)
        wait_for_enter()
        return

    print_color("Which service?", Colors.BOLD)
    print()

    for i, svc in enumerate(web_services, 1):
        creds = ""
        if svc.get("credentials"):
            creds = f" {Colors.DIM}[{svc['credentials']}]{Colors.NC}"
        print(f"  {Colors.BOLD}{i}{Colors.NC}) {svc['name']} → {svc['url']}{creds}")

    print(f"  {Colors.BOLD}b{Colors.NC}) Back")
    print()

    choice = get_input()

    if choice in ("b", "back"):
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(web_services):
            svc = web_services[idx]
            url = svc["url"]

            print()
            print_color(f"Opening {svc['name']} in browser...", Colors.CYAN)

            if svc.get("credentials"):
                print()
                print_color(f"Login credentials: {svc['credentials']}", Colors.YELLOW)

            webbrowser.open(url)
            wait_for_enter()
    except ValueError:
        pass


def view_logs_menu(running: list[dict], all_profiles: list[str]):
    """Menu to select which service logs to view."""
    clear_screen()
    print_header("View logs")

    print_color("Which service?", Colors.BOLD)
    print()
    print(f"  {Colors.BOLD}0{Colors.NC}) All services")

    for i, svc in enumerate(running, 1):
        print(f"  {Colors.BOLD}{i}{Colors.NC}) {svc['name']}")

    print(f"  {Colors.BOLD}b{Colors.NC}) Back")
    print()

    choice = get_input()

    if choice in ("b", "back"):
        return

    service_name = None
    service_id = None

    if choice == "0":
        service_name = "all services"
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(running):
                svc = running[idx]
                service_name = svc['name']
                service_id = svc["id"]
        except ValueError:
            return

    if service_name:
        print_color(f"\nShowing logs for {service_name} (Ctrl+C to return)...\n", Colors.CYAN)
        try:
            docker.get_logs(all_profiles, service_id)
        except KeyboardInterrupt:
            # User pressed Ctrl+C, return to menu gracefully
            print()
            print_color("\nReturning to menu...", Colors.DIM)
        wait_for_enter()


def shell_menu(running: list[dict]):
    """Menu to select which service to shell into."""
    clear_screen()
    print_header("Open shell")

    print_color("Which service?", Colors.BOLD)
    print()

    for i, svc in enumerate(running, 1):
        print(f"  {Colors.BOLD}{i}{Colors.NC}) {svc['name']}")

    print(f"  {Colors.BOLD}b{Colors.NC}) Back")
    print()

    choice = get_input()

    if choice in ("b", "back"):
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(running):
            svc = running[idx]
            print_color(f"\nOpening shell in {svc['name']} (type 'exit' to return)...\n", Colors.CYAN)
            try:
                docker.open_shell(svc["container"])
            except KeyboardInterrupt:
                print()
            wait_for_enter()
    except ValueError:
        pass


def rebuild_menu(running: list[dict], all_profiles: list[str]):
    """Menu to rebuild service images."""
    clear_screen()
    print_header("Rebuild services")

    print_color("Which service to rebuild?", Colors.BOLD)
    print()
    print(f"  {Colors.BOLD}0{Colors.NC}) All running services")

    for i, svc in enumerate(running, 1):
        print(f"  {Colors.BOLD}{i}{Colors.NC}) {svc['name']}")

    print(f"  {Colors.BOLD}b{Colors.NC}) Back")
    print()

    choice = get_input()

    if choice in ("b", "back"):
        return

    if choice == "0":
        print_color("\nRebuilding and restarting all services...", Colors.CYAN)
        running_profiles = [r["id"] for r in running]
        docker.build_services(running_profiles)
        docker.compose_command(["up", "-d", "--build"], running_profiles)
        print_color("Rebuild complete.", Colors.GREEN)
        wait_for_enter()
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(running):
                svc = running[idx]
                print_color(f"\nRebuilding {svc['name']}...", Colors.CYAN)
                docker.build_services([svc["id"]])
                docker.compose_command(["up", "-d", "--build"], [svc["id"]])
                print_color("Rebuild complete.", Colors.GREEN)
                wait_for_enter()
        except ValueError:
            pass


def restart_menu(running: list[dict], all_profiles: list[str]):
    """Menu to restart services."""
    clear_screen()
    print_header("Restart services")

    print_color("What to restart?", Colors.BOLD)
    print()
    print(f"  {Colors.BOLD}0{Colors.NC}) All running services")

    for i, svc in enumerate(running, 1):
        print(f"  {Colors.BOLD}{i}{Colors.NC}) {svc['name']}")

    print(f"  {Colors.BOLD}b{Colors.NC}) Back")
    print()

    choice = get_input()

    if choice in ("b", "back"):
        return

    if choice == "0":
        print_color("\nRestarting all services...", Colors.CYAN)
        running_profiles = [r["id"] for r in running]
        docker.restart_services(running_profiles)
        print_color("Services restarted.", Colors.GREEN)
        wait_for_enter()
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(running):
                svc = running[idx]
                print_color(f"\nRestarting {svc['name']}...", Colors.CYAN)
                docker.restart_services([svc["id"]])
                print_color("Service restarted.", Colors.GREEN)
                wait_for_enter()
        except ValueError:
            pass


def stop_menu(running: list[dict], all_profiles: list[str]):
    """Menu to stop services."""
    clear_screen()
    print_header("Stop services")

    print_color("What to stop?", Colors.BOLD)
    print()
    print(f"  {Colors.BOLD}0{Colors.NC}) All services")
    print(f"  {Colors.BOLD}c{Colors.NC}) Clean (stop + remove volumes)")
    print(f"  {Colors.BOLD}n{Colors.NC}) Nuclear (remove EVERYTHING)")

    for i, svc in enumerate(running, 1):
        print(f"  {Colors.BOLD}{i}{Colors.NC}) {svc['name']}")

    print(f"  {Colors.BOLD}b{Colors.NC}) Back")
    print()

    choice = get_input()

    if choice in ("b", "back"):
        return

    if choice == "0":
        print_color("\nStopping all services...", Colors.CYAN)
        docker.stop_services(all_profiles)
        print_color("All services stopped.", Colors.GREEN)
        wait_for_enter()

    elif choice == "c":
        print()
        print_color("WARNING: This will remove all volumes (databases, logs, etc.)!", Colors.RED)
        confirm = get_input("Type 'yes' to confirm: ")
        if confirm == "yes":
            print_color("\nStopping and cleaning...", Colors.CYAN)
            docker.clean_services(all_profiles)
            print_color("Clean complete.", Colors.GREEN)
        else:
            print_color("Cancelled.", Colors.YELLOW)
        wait_for_enter()

    elif choice == "n":
        nuclear_clean_prompt(all_profiles)

    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(running):
                svc = running[idx]
                print_color(f"\nStopping {svc['name']}...", Colors.CYAN)
                docker.stop_services([svc["id"]])
                print_color("Service stopped.", Colors.GREEN)
                wait_for_enter()
        except ValueError:
            pass


def nuclear_clean_prompt(all_profiles: list[str]):
    """Prompt for nuclear clean with confirmation."""
    print()
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

    confirm = get_input("Type 'nuke' to confirm: ")
    if confirm == "nuke":
        print()
        print_color("Nuking everything...", Colors.RED)
        print()
        docker.nuclear_clean(all_profiles)
        print()
        print_color("Nuclear clean complete. Everything has been removed.", Colors.GREEN)
    else:
        print_color("Cancelled.", Colors.YELLOW)
    wait_for_enter()


# =============================================================================
# HEALTH CHECKS
# =============================================================================

def run_health_checks(services: dict[str, Service], running: list[dict]):
    """Run and display health checks."""
    print()
    print_color("Running health checks...", Colors.CYAN)
    print()

    import urllib.request
    import urllib.error

    for r in running:
        service = services.get(r["id"])
        if not service or not service.healthcheck:
            continue

        hc = service.healthcheck

        if hc.type == "http" and hc.endpoint:
            try:
                urllib.request.urlopen(hc.endpoint, timeout=5)
                print(f"  {Colors.GREEN}✓{Colors.NC} {service.name} - accepting connections")
            except (urllib.error.URLError, TimeoutError):
                print(f"  {Colors.YELLOW}~{Colors.NC} {service.name} - not responding")

        elif hc.type == "exec" and hc.command:
            result = docker.exec_in_container(r["container"], hc.command)
            if result.returncode == 0:
                print(f"  {Colors.GREEN}✓{Colors.NC} {service.name} - accepting connections")
            else:
                print(f"  {Colors.RED}✗{Colors.NC} {service.name} - not ready")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def interactive_mode():
    """Run the interactive CLI."""
    services = discover_services()
    all_profiles = list(services.keys())

    while True:
        running = get_running_services(services)

        if running:
            if not menu_services_running(services, all_profiles, running):
                break
        else:
            if not menu_no_services(services, all_profiles):
                break
