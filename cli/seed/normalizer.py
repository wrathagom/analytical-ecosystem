"""Normalization logic for relational databases."""

from typing import Any


class DataNormalizer:
    """Normalizes flat data into related tables for relational databases."""

    def __init__(self):
        self.customers: dict[str, dict] = {}
        self.products: dict[str, dict] = {}
        self._customer_id_counter = 1
        self._product_id_counter = 1

    def _extract_customer(self, record: dict[str, Any]) -> int | None:
        """Extract customer info and return customer_id."""
        # Look for customer fields in the record
        customer_email = record.get("customer_email")
        if not customer_email:
            return None

        # Check if we've seen this customer before
        if customer_email in self.customers:
            return self.customers[customer_email]["id"]

        # Create new customer
        customer = {
            "id": self._customer_id_counter,
            "name": record.get("customer_name", ""),
            "email": customer_email,
            "phone": record.get("customer_phone", ""),
        }
        self.customers[customer_email] = customer
        self._customer_id_counter += 1

        return customer["id"]

    def _extract_product(self, record: dict[str, Any]) -> int | None:
        """Extract product info and return product_id."""
        # Look for product fields in the record
        product_sku = record.get("product_sku") or record.get("sku")
        if not product_sku:
            return None

        # Check if we've seen this product before
        if product_sku in self.products:
            return self.products[product_sku]["id"]

        # Create new product
        product = {
            "id": self._product_id_counter,
            "sku": product_sku,
            "name": record.get("product_name") or record.get("name", ""),
        }
        self.products[product_sku] = product
        self._product_id_counter += 1

        return product["id"]

    def normalize_record(
        self,
        record: dict[str, Any],
        schema_name: str,
    ) -> dict[str, Any]:
        """
        Normalize a record by extracting related entities.
        Returns modified record with foreign keys instead of denormalized data.
        """
        normalized = record.copy()

        # Extract customer if applicable
        if schema_name in ("sales_orders", "invoices"):
            customer_id = self._extract_customer(record)
            if customer_id:
                normalized["customer_id"] = customer_id
                # Remove denormalized customer fields
                for field in ["customer_name", "customer_email", "customer_phone"]:
                    normalized.pop(field, None)

        # Extract product if applicable
        if schema_name == "manufacturing_orders":
            product_id = self._extract_product(record)
            if product_id:
                normalized["product_id"] = product_id
                # Remove denormalized product fields
                for field in ["product_name", "product_sku"]:
                    normalized.pop(field, None)

        return normalized

    def get_customers_table(self) -> list[dict[str, Any]]:
        """Get the extracted customers as a list."""
        return list(self.customers.values())

    def get_products_table(self) -> list[dict[str, Any]]:
        """Get the extracted products as a list."""
        return list(self.products.values())

    def get_customer_schema_sql(self) -> str:
        """Get SQL to create customers table."""
        return """
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            phone VARCHAR(50)
        )
        """

    def get_product_schema_sql(self) -> str:
        """Get SQL to create products table (normalized version)."""
        return """
        CREATE TABLE IF NOT EXISTS products_normalized (
            id SERIAL PRIMARY KEY,
            sku VARCHAR(50) UNIQUE,
            name VARCHAR(255)
        )
        """

    def reset(self):
        """Reset the normalizer state."""
        self.customers.clear()
        self.products.clear()
        self._customer_id_counter = 1
        self._product_id_counter = 1
