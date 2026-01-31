"""Abstract base class for database backends."""

from abc import ABC, abstractmethod
from typing import Any

from ..schemas import Schema


class DatabaseBackend(ABC):
    """Abstract base class for database backends."""

    name: str = "base"
    supports_normalization: bool = False

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the database."""
        pass

    @abstractmethod
    def create_table(self, schema: Schema, normalized: bool = False) -> None:
        """Create the table for the given schema."""
        pass

    @abstractmethod
    def insert_batch(
        self,
        schema: Schema,
        records: list[dict[str, Any]],
        normalized: bool = False,
    ) -> int:
        """
        Insert a batch of records.
        Returns the number of records inserted.
        """
        pass

    @abstractmethod
    def get_count(self, table_name: str) -> int:
        """Get the count of records in a table."""
        pass

    def create_normalized_tables(self) -> None:
        """Create normalized reference tables (customers, products)."""
        pass

    def insert_normalized_entities(
        self,
        customers: list[dict[str, Any]],
        products: list[dict[str, Any]],
    ) -> None:
        """Insert normalized entity tables."""
        pass

    def is_healthy(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            self.connect()
            self.disconnect()
            return True
        except Exception:
            return False

    def get_connection_info(self) -> dict[str, str]:
        """Get connection information for display to user."""
        return {}

    def truncate_table(self, table_name: str) -> None:
        """Truncate (clear all data from) a table."""
        pass

    def drop_table(self, table_name: str) -> None:
        """Drop a table if it exists."""
        pass
