#!/usr/bin/env python3
"""
Analytical Ecosystem CLI

Manage Docker Compose services for the analytical ecosystem.
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from cli.config import discover_services
from cli.commands import (
    cmd_list, cmd_start, cmd_stop, cmd_restart, cmd_status,
    cmd_logs, cmd_build, cmd_clean, cmd_nuke, cmd_shell, cmd_test, cmd_env,
)
from cli.ui import interactive_mode


def main():
    parser = argparse.ArgumentParser(
        description="Analytical Ecosystem CLI - Manage Docker Compose services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    Interactive mode
  %(prog)s --profiles postgres,jupyter start  Start specific services
  %(prog)s stop                               Stop all services
  %(prog)s status                             Show running services
  %(prog)s logs jupyter                       Show logs for jupyter
  %(prog)s shell postgres                     Open shell in postgres
  %(prog)s test                               Run health checks
  %(prog)s clean                              Stop and remove volumes
""",
    )

    parser.add_argument(
        "--profiles", "-p",
        help="Comma-separated list of service profiles",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Commands
    subparsers.add_parser("list", help="List available services")
    subparsers.add_parser("start", help="Start selected services")
    subparsers.add_parser("stop", help="Stop all services")
    subparsers.add_parser("restart", help="Restart services")
    subparsers.add_parser("status", help="Show running services")

    logs_parser = subparsers.add_parser("logs", help="Show service logs")
    logs_parser.add_argument("service", nargs="?", help="Service name")

    subparsers.add_parser("build", help="Build service images")
    subparsers.add_parser("clean", help="Stop and remove all volumes")
    subparsers.add_parser("nuke", help="Nuclear clean - remove everything")

    shell_parser = subparsers.add_parser("shell", help="Open shell in container")
    shell_parser.add_argument("service", nargs="?", help="Service name")

    subparsers.add_parser("test", help="Run health checks")
    env_parser = subparsers.add_parser("env", help="Generate .env from fragments")
    env_parser.add_argument(
        "--output", "-o",
        default=".env.example",
        help="Output path for generated env file",
    )

    args = parser.parse_args()

    # Parse profiles
    profiles = []
    if args.profiles:
        profiles = [p.strip() for p in args.profiles.split(",")]

    # Get all profiles for commands that need them
    services = discover_services()
    all_profiles = list(services.keys())

    # If no command, run interactive mode
    if not args.command:
        interactive_mode()
        return 0

    # Dispatch commands
    if args.command == "list":
        cmd_list()

    elif args.command == "start":
        if not profiles:
            print("No profiles specified. Use --profiles or interactive mode.")
            return 1
        success = cmd_start(profiles)
        return 0 if success else 1

    elif args.command == "stop":
        cmd_stop(profiles or all_profiles)

    elif args.command == "restart":
        cmd_restart(profiles or all_profiles)

    elif args.command == "status":
        cmd_status()

    elif args.command == "logs":
        cmd_logs(profiles or all_profiles, args.service)

    elif args.command == "build":
        cmd_build(profiles or all_profiles)

    elif args.command == "clean":
        cmd_clean(profiles or all_profiles)

    elif args.command == "nuke":
        cmd_nuke(profiles or all_profiles)

    elif args.command == "shell":
        cmd_shell(args.service or "")

    elif args.command == "test":
        success = cmd_test()
        return 0 if success else 1

    elif args.command == "env":
        success = cmd_env(profiles or all_profiles, args.output)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
