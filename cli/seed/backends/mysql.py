"""MySQL database backend."""

import os
from typing import Any
from datetime import datetime

from .base import DatabaseBackend
from ..schemas import Schema


class MySQLBackend(DatabaseBackend):
    """MySQL database backend using pymysql."""

    name = "mysql"
    supports_normalization = True

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
    ):
        self.host = host or os.environ.get("MYSQL_HOST", "localhost")
        self.port = port or int(os.environ.get("MYSQL_PORT", "3306"))
        self.user = user or os.environ.get("MYSQL_USER", "analyticsUser")
        self.password = password or os.environ.get("MYSQL_PASSWORD", "analyticsPass")
        self.database = database or os.environ.get("MYSQL_DB", "analytics")
        self.conn = None

    def get_connection_info(self) -> dict[str, str]:
        """Get connection information for display to user."""
        return {
            "host": self.host,
            "port": str(self.port),
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "connect_cmd": f"mysql -h {self.host} -P {self.port} -u {self.user} -p {self.database}",
        }

    def connect(self) -> None:
        """Establish connection to MySQL."""
        import pymysql

        if self.conn is None:
            self.conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=False,
            )

    def disconnect(self) -> None:
        """Close connection to MySQL."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _convert_sql_type(self, sql_type: str) -> str:
        """Convert PostgreSQL-style types to MySQL."""
        # Handle SERIAL -> AUTO_INCREMENT
        if "SERIAL" in sql_type:
            return sql_type.replace("SERIAL", "INT AUTO_INCREMENT")

        # Handle TIMESTAMP
        if sql_type == "TIMESTAMP":
            return "DATETIME"

        # Handle TEXT (MySQL prefers VARCHAR for indexed columns)
        return sql_type

    def _get_column_def(self, field) -> str:
        """Get column definition for a field, handling MySQL specifics."""
        sql_type = self._convert_sql_type(field.sql_type)

        # Handle id column
        if field.name == "id":
            return "id INT AUTO_INCREMENT PRIMARY KEY"

        # Handle nullable
        null_clause = "" if field.nullable else " NOT NULL"

        # Handle UNIQUE constraint
        if "UNIQUE" in sql_type:
            sql_type = sql_type.replace(" UNIQUE", "")
            return f"{field.name} {sql_type}{null_clause} UNIQUE"

        return f"{field.name} {sql_type}{null_clause}"

    def create_table(self, schema: Schema, normalized: bool = False) -> None:
        """Create the table for the given schema."""
        self.connect()
        cursor = self.conn.cursor()

        # Build column definitions
        columns = []
        for field in schema.fields:
            if field.name == "id":
                columns.append("id INT AUTO_INCREMENT PRIMARY KEY")
            else:
                col_def = self._get_column_def(field)
                columns.append(col_def)

        # Handle normalized schema modifications
        if normalized:
            if schema.name in ("sales_orders", "invoices"):
                columns.append("customer_id INT")
                columns.append("FOREIGN KEY (customer_id) REFERENCES customers(id)")
                # Remove denormalized customer columns
                columns = [c for c in columns if not any(
                    c.startswith(f) for f in ["customer_name ", "customer_email ", "customer_phone "]
                )]

            if schema.name == "manufacturing_orders":
                columns.append("product_id INT")
                columns.append("FOREIGN KEY (product_id) REFERENCES products_normalized(id)")
                # Remove denormalized product columns
                columns = [c for c in columns if not any(
                    c.startswith(f) for f in ["product_name ", "product_sku "]
                )]

        table_name = schema.table_name
        if normalized:
            table_name = f"{schema.table_name}_normalized"

        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)}) ENGINE=InnoDB"

        cursor.execute(sql)
        self.conn.commit()
        cursor.close()

    def create_normalized_tables(self) -> None:
        """Create normalized reference tables."""
        self.connect()
        cursor = self.conn.cursor()

        # Create customers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(50)
            ) ENGINE=InnoDB
        """)

        # Create products_normalized table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products_normalized (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sku VARCHAR(50) UNIQUE,
                name VARCHAR(255)
            ) ENGINE=InnoDB
        """)

        self.conn.commit()
        cursor.close()

    def insert_normalized_entities(
        self,
        customers: list[dict[str, Any]],
        products: list[dict[str, Any]],
    ) -> None:
        """Insert normalized entity tables."""
        self.connect()
        cursor = self.conn.cursor()

        # Insert customers
        for customer in customers:
            cursor.execute(
                """
                INSERT IGNORE INTO customers (id, name, email, phone)
                VALUES (%s, %s, %s, %s)
                """,
                (customer["id"], customer["name"], customer["email"], customer["phone"])
            )

        # Insert products
        for product in products:
            cursor.execute(
                """
                INSERT IGNORE INTO products_normalized (id, sku, name)
                VALUES (%s, %s, %s)
                """,
                (product["id"], product["sku"], product["name"])
            )

        self.conn.commit()
        cursor.close()

    def insert_batch(
        self,
        schema: Schema,
        records: list[dict[str, Any]],
        normalized: bool = False,
    ) -> int:
        """Insert a batch of records."""
        if not records:
            return 0

        self.connect()
        cursor = self.conn.cursor()

        table_name = schema.table_name
        if normalized:
            table_name = f"{schema.table_name}_normalized"

        # Get columns from the first record (excluding id)
        columns = [k for k in records[0].keys() if k != "id"]
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join(columns)

        # Use INSERT IGNORE to handle unique constraint violations gracefully
        sql = f"INSERT IGNORE INTO {table_name} ({column_names}) VALUES ({placeholders})"

        inserted = 0
        for record in records:
            values = []
            for col in columns:
                value = record.get(col)
                # Convert datetime objects
                if isinstance(value, datetime):
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                values.append(value)

            cursor.execute(sql, values)
            inserted += cursor.rowcount

        self.conn.commit()
        cursor.close()
        return inserted

    def get_count(self, table_name: str) -> int:
        """Get the count of records in a table."""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.close()
        return count

    def truncate_table(self, table_name: str) -> None:
        """Truncate a table, handling foreign key constraints."""
        self.connect()
        cursor = self.conn.cursor()
        # Disable FK checks, truncate, re-enable
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute(f"TRUNCATE TABLE {table_name}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        self.conn.commit()
        cursor.close()

    def drop_table(self, table_name: str) -> None:
        """Drop a table if it exists."""
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        self.conn.commit()
        cursor.close()
