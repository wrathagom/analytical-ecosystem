"""Backend registry and factory."""

from typing import Type

from .base import DatabaseBackend
from .postgres import PostgresBackend
from .mysql import MySQLBackend
from .elasticsearch import ElasticsearchBackend
from .duckdb import DuckDBBackend


# Registry of available backends
BACKENDS: dict[str, Type[DatabaseBackend]] = {
    "postgres": PostgresBackend,
    "mysql": MySQLBackend,
    "elasticsearch": ElasticsearchBackend,
    "duckdb": DuckDBBackend,
}

# Aliases for convenience
BACKEND_ALIASES: dict[str, str] = {
    "pg": "postgres",
    "postgresql": "postgres",
    "es": "elasticsearch",
    "elastic": "elasticsearch",
    "duck": "duckdb",
}


def get_backend(name: str) -> DatabaseBackend:
    """
    Get a backend instance by name.

    Args:
        name: Backend name (postgres, mysql, elasticsearch) or alias

    Returns:
        Configured backend instance

    Raises:
        ValueError: If backend name is unknown
    """
    # Resolve aliases
    resolved_name = BACKEND_ALIASES.get(name.lower(), name.lower())

    if resolved_name not in BACKENDS:
        available = list(BACKENDS.keys())
        raise ValueError(
            f"Unknown backend: {name}. Available backends: {available}"
        )

    backend_class = BACKENDS[resolved_name]
    return backend_class()


def list_backends() -> list[tuple[str, bool]]:
    """
    List available backends with their normalization support.

    Returns:
        List of (name, supports_normalization) tuples
    """
    result = []
    for name, backend_class in BACKENDS.items():
        instance = backend_class()
        result.append((name, instance.supports_normalization))
    return result


def get_seedable_backends() -> list[str]:
    """Get list of backend names that can be seeded."""
    return list(BACKENDS.keys())
