"""DuckDB database backend."""

import os
from typing import Any
from datetime import datetime

from .base import DatabaseBackend
from ..schemas import Schema


class DuckDBBackend(DatabaseBackend):
    """DuckDB backend using the duckdb Python package."""

    name = "duckdb"
    supports_normalization = True

    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("DUCKDB_PATH", "./shared/data/duckdb.db")
        self.conn = None
        self._id_counters: dict[str, int] = {}

    def get_connection_info(self) -> dict[str, str]:
        return {
            "database": self.path,
            "connect_cmd": f"duckdb {self.path}",
        }

    def connect(self) -> None:
        import duckdb

        if self.conn is None:
            self.conn = duckdb.connect(self.path)

    def disconnect(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _convert_sql_type(self, sql_type: str) -> str:
        """Convert PostgreSQL-style types to DuckDB."""
        if "SERIAL" in sql_type:
            return "INTEGER"
        if sql_type == "TIMESTAMP":
            return "TIMESTAMP"
        return sql_type

    def _get_column_def(self, field) -> str:
        sql_type = self._convert_sql_type(field.sql_type)

        if field.name == "id":
            return "id INTEGER PRIMARY KEY"

        null_clause = "" if field.nullable else " NOT NULL"

        if "UNIQUE" in sql_type:
            sql_type = sql_type.replace(" UNIQUE", "")
            return f"{field.name} {sql_type}{null_clause} UNIQUE"

        return f"{field.name} {sql_type}{null_clause}"

    def create_table(self, schema: Schema, normalized: bool = False) -> None:
        self.connect()
        cursor = self.conn.cursor()

        columns = []
        for field in schema.fields:
            if field.name == "id":
                columns.append("id INTEGER PRIMARY KEY")
            else:
                columns.append(self._get_column_def(field))

        if normalized:
            if schema.name in ("sales_orders", "invoices"):
                columns.append("customer_id INTEGER")
                columns = [c for c in columns if not any(
                    c.startswith(f) for f in ["customer_name ", "customer_email ", "customer_phone "]
                )]

            if schema.name == "manufacturing_orders":
                columns.append("product_id INTEGER")
                columns = [c for c in columns if not any(
                    c.startswith(f) for f in ["product_name ", "product_sku "]
                )]

        table_name = schema.table_name
        if normalized:
            table_name = f"{schema.table_name}_normalized"

        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        cursor.execute(sql)
        self.conn.commit()
        cursor.close()

    def create_normalized_tables(self) -> None:
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                email VARCHAR UNIQUE,
                phone VARCHAR
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products_normalized (
                id INTEGER PRIMARY KEY,
                sku VARCHAR UNIQUE,
                name VARCHAR
            )
            """
        )

        self.conn.commit()
        cursor.close()

    def insert_normalized_entities(
        self,
        customers: list[dict[str, Any]],
        products: list[dict[str, Any]],
    ) -> None:
        self.connect()
        cursor = self.conn.cursor()

        if customers:
            cursor.executemany(
                "INSERT OR IGNORE INTO customers (id, name, email, phone) VALUES (?, ?, ?, ?)",
                [(c["id"], c["name"], c["email"], c["phone"]) for c in customers],
            )

        if products:
            cursor.executemany(
                "INSERT OR IGNORE INTO products_normalized (id, sku, name) VALUES (?, ?, ?)",
                [(p["id"], p["sku"], p["name"]) for p in products],
            )

        self.conn.commit()
        cursor.close()

    def insert_batch(
        self,
        schema: Schema,
        records: list[dict[str, Any]],
        normalized: bool = False,
    ) -> int:
        if not records:
            return 0

        self.connect()
        cursor = self.conn.cursor()

        table_name = schema.table_name
        if normalized:
            table_name = f"{schema.table_name}_normalized"

        # Ensure records have IDs if the schema expects them.
        if records:
            needs_id = "id" not in records[0]
            has_null_id = any(record.get("id") is None for record in records)
            if needs_id or has_null_id:
                if table_name not in self._id_counters:
                    cursor.execute(f"SELECT MAX(id) FROM {table_name}")
                    max_id = cursor.fetchone()[0] or 0
                    self._id_counters[table_name] = int(max_id) + 1

                next_id = self._id_counters[table_name]
                for record in records:
                    if record.get("id") is None:
                        record["id"] = next_id
                        next_id += 1
                self._id_counters[table_name] = next_id

        columns = list(records[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        column_names = ", ".join(columns)

        sql = f"INSERT OR IGNORE INTO {table_name} ({column_names}) VALUES ({placeholders})"

        values = []
        for record in records:
            row = []
            for col in columns:
                value = record.get(col)
                if isinstance(value, datetime):
                    value = value.isoformat()
                row.append(value)
            values.append(tuple(row))

        cursor.executemany(sql, values)
        self.conn.commit()
        cursor.close()
        return len(records)

    def get_count(self, table_name: str) -> int:
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.close()
        return count

    def truncate_table(self, table_name: str) -> None:
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM {table_name}")
        self.conn.commit()
        cursor.close()

    def drop_table(self, table_name: str) -> None:
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.conn.commit()
        cursor.close()
