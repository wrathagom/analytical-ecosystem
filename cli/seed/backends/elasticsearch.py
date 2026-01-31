"""Elasticsearch database backend."""

import os
from typing import Any
from datetime import datetime

from .base import DatabaseBackend
from ..schemas import Schema


class ElasticsearchBackend(DatabaseBackend):
    """Elasticsearch backend using elasticsearch-py."""

    name = "elasticsearch"
    supports_normalization = False

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
    ):
        self.host = host or os.environ.get("ELASTICSEARCH_HOST", "localhost")
        self.port = port or int(os.environ.get("ELASTICSEARCH_PORT", "9200"))
        self.client = None

    def get_connection_info(self) -> dict[str, str]:
        """Get connection information for display to user."""
        return {
            "host": self.host,
            "port": str(self.port),
            "url": f"http://{self.host}:{self.port}",
            "connect_cmd": f"curl http://{self.host}:{self.port}/_cat/indices?v",
        }

    def connect(self) -> None:
        """Establish connection to Elasticsearch."""
        from elasticsearch import Elasticsearch

        if self.client is None:
            self.client = Elasticsearch(
                hosts=[{"host": self.host, "port": self.port, "scheme": "http"}],
            )

    def disconnect(self) -> None:
        """Close connection to Elasticsearch."""
        if self.client:
            self.client.close()
            self.client = None

    def create_table(self, schema: Schema, normalized: bool = False) -> None:
        """Create the index for the given schema."""
        self.connect()

        index_name = schema.table_name
        mapping = schema.get_es_mapping()

        # Create index if it doesn't exist
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(index=index_name, body=mapping)

    def insert_batch(
        self,
        schema: Schema,
        records: list[dict[str, Any]],
        normalized: bool = False,
    ) -> int:
        """Insert a batch of records using bulk API."""
        if not records:
            return 0

        self.connect()

        index_name = schema.table_name

        # Prepare bulk operations
        operations = []
        for record in records:
            # Convert datetime objects to ISO format
            doc = {}
            for key, value in record.items():
                if isinstance(value, datetime):
                    doc[key] = value.isoformat()
                else:
                    doc[key] = value

            operations.append({"index": {"_index": index_name}})
            operations.append(doc)

        # Execute bulk insert
        if operations:
            response = self.client.bulk(body=operations, refresh=True)
            # Count successful inserts
            if response.get("errors"):
                # Count non-error items
                inserted = sum(
                    1 for item in response.get("items", [])
                    if "error" not in item.get("index", {})
                )
            else:
                inserted = len(records)
            return inserted

        return 0

    def get_count(self, table_name: str) -> int:
        """Get the count of documents in an index."""
        self.connect()

        try:
            result = self.client.count(index=table_name)
            return result.get("count", 0)
        except Exception:
            return 0

    def is_healthy(self) -> bool:
        """Check if Elasticsearch is healthy."""
        try:
            self.connect()
            health = self.client.cluster.health()
            return health.get("status") in ("green", "yellow")
        except Exception:
            return False

    def truncate_table(self, table_name: str) -> None:
        """Delete all documents from an index."""
        self.connect()
        try:
            # Delete by query - match all documents
            self.client.delete_by_query(
                index=table_name,
                body={"query": {"match_all": {}}},
                refresh=True,
            )
        except Exception:
            pass  # Index might not exist

    def drop_table(self, table_name: str) -> None:
        """Delete an index."""
        self.connect()
        try:
            self.client.indices.delete(index=table_name, ignore=[404])
        except Exception:
            pass
