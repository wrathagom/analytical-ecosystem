"""Data schema definitions for seed data generation."""

from dataclasses import dataclass, field
from typing import Callable, Any
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()


@dataclass
class FieldDef:
    """Definition for a single field in a schema."""
    name: str
    faker_func: Callable[[], Any]
    sql_type: str = "TEXT"
    es_type: str = "text"
    nullable: bool = False


@dataclass
class Schema:
    """Definition for a data schema."""
    name: str
    table_name: str
    description: str
    time_field: str
    fields: list[FieldDef] = field(default_factory=list)

    def get_field_names(self) -> list[str]:
        """Get list of field names."""
        return [f.name for f in self.fields]

    def get_sql_columns(self) -> list[tuple[str, str]]:
        """Get list of (name, type) for SQL schema."""
        return [(f.name, f.sql_type) for f in self.fields]

    def get_es_mapping(self) -> dict:
        """Get Elasticsearch mapping for this schema."""
        properties = {}
        for f in self.fields:
            if f.es_type == "text":
                properties[f.name] = {"type": "text", "fields": {"keyword": {"type": "keyword"}}}
            elif f.es_type == "date":
                properties[f.name] = {"type": "date"}
            elif f.es_type == "integer":
                properties[f.name] = {"type": "integer"}
            elif f.es_type == "float":
                properties[f.name] = {"type": "float"}
            elif f.es_type == "boolean":
                properties[f.name] = {"type": "boolean"}
            else:
                properties[f.name] = {"type": f.es_type}
        return {"mappings": {"properties": properties}}


def _gen_id() -> int:
    """Generate a unique ID (placeholder, actual IDs are auto-incremented)."""
    return fake.random_int(min=1, max=999999)


def _gen_order_number() -> str:
    return f"ORD-{fake.uuid4()[:12].upper()}"


def _gen_work_order_number() -> str:
    return f"WO-{fake.uuid4()[:12].upper()}"


def _gen_invoice_number() -> str:
    return f"INV-{fake.uuid4()[:12].upper()}"


def _gen_sku() -> str:
    return f"SKU-{fake.uuid4()[:10].upper()}"


def _gen_status_order() -> str:
    return fake.random_element(["pending", "processing", "shipped", "delivered", "cancelled"])


def _gen_status_manufacturing() -> str:
    return fake.random_element(["planned", "in_progress", "completed", "on_hold", "cancelled"])


def _gen_status_invoice() -> str:
    return fake.random_element(["draft", "sent", "paid", "overdue", "cancelled"])


def _gen_priority() -> str:
    return fake.random_element(["low", "medium", "high", "urgent"])


def _gen_payment_method() -> str:
    return fake.random_element(["credit_card", "debit_card", "bank_transfer", "paypal", "check", "cash"])


def _gen_unit_of_measure() -> str:
    return fake.random_element(["each", "box", "case", "pallet", "kg", "lb", "liter", "gallon"])


def _gen_category() -> str:
    return fake.random_element([
        "Electronics", "Clothing", "Home & Garden", "Sports", "Automotive",
        "Books", "Toys", "Health", "Food & Beverage", "Office Supplies"
    ])


def _gen_line_items_json() -> str:
    """Generate JSON string of line items."""
    import json
    items = []
    for _ in range(fake.random_int(min=1, max=5)):
        items.append({
            "description": fake.catch_phrase(),
            "quantity": fake.random_int(min=1, max=10),
            "unit_price": round(fake.pyfloat(min_value=10, max_value=500, right_digits=2), 2)
        })
    return json.dumps(items)


# Schema definitions
CONTACTS = Schema(
    name="contacts",
    table_name="contacts",
    description="Customer and business contacts",
    time_field="created_at",
    fields=[
        FieldDef("id", _gen_id, "SERIAL PRIMARY KEY", "integer"),
        FieldDef("first_name", fake.first_name, "VARCHAR(100)", "text"),
        FieldDef("last_name", fake.last_name, "VARCHAR(100)", "text"),
        FieldDef("email", fake.email, "VARCHAR(255)", "keyword"),
        FieldDef("phone", fake.phone_number, "VARCHAR(50)", "keyword"),
        FieldDef("company", fake.company, "VARCHAR(255)", "text"),
        FieldDef("job_title", fake.job, "VARCHAR(255)", "text"),
        FieldDef("address", fake.street_address, "VARCHAR(255)", "text"),
        FieldDef("city", fake.city, "VARCHAR(100)", "keyword"),
        FieldDef("state", fake.state_abbr, "VARCHAR(50)", "keyword"),
        FieldDef("postal_code", fake.postcode, "VARCHAR(20)", "keyword"),
        FieldDef("country", fake.country, "VARCHAR(100)", "keyword"),
        FieldDef("created_at", fake.date_time_this_year, "TIMESTAMP", "date"),
        FieldDef("updated_at", fake.date_time_this_year, "TIMESTAMP", "date"),
    ]
)

SALES_ORDERS = Schema(
    name="sales_orders",
    table_name="sales_orders",
    description="Sales order records",
    time_field="order_date",
    fields=[
        FieldDef("id", _gen_id, "SERIAL PRIMARY KEY", "integer"),
        FieldDef("order_number", _gen_order_number, "VARCHAR(50) UNIQUE", "keyword"),
        FieldDef("customer_name", fake.name, "VARCHAR(255)", "text"),
        FieldDef("customer_email", fake.email, "VARCHAR(255)", "keyword"),
        FieldDef("customer_phone", fake.phone_number, "VARCHAR(50)", "keyword"),
        FieldDef("order_date", fake.date_time_this_year, "TIMESTAMP", "date"),
        FieldDef("ship_date", fake.date_time_this_year, "TIMESTAMP", "date", nullable=True),
        FieldDef("status", _gen_status_order, "VARCHAR(50)", "keyword"),
        FieldDef("subtotal", lambda: round(fake.pyfloat(min_value=10, max_value=1000, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("tax", lambda: round(fake.pyfloat(min_value=1, max_value=100, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("shipping", lambda: round(fake.pyfloat(min_value=5, max_value=50, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("total", lambda: round(fake.pyfloat(min_value=20, max_value=1200, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("shipping_address", fake.street_address, "VARCHAR(255)", "text"),
        FieldDef("shipping_city", fake.city, "VARCHAR(100)", "keyword"),
        FieldDef("shipping_state", fake.state_abbr, "VARCHAR(50)", "keyword"),
        FieldDef("shipping_postal_code", fake.postcode, "VARCHAR(20)", "keyword"),
        FieldDef("payment_method", _gen_payment_method, "VARCHAR(50)", "keyword"),
        FieldDef("notes", lambda: fake.text(max_nb_chars=200), "TEXT", "text", nullable=True),
        FieldDef("created_at", fake.date_time_this_year, "TIMESTAMP", "date"),
    ]
)

MANUFACTURING_ORDERS = Schema(
    name="manufacturing_orders",
    table_name="manufacturing_orders",
    description="Production work orders",
    time_field="scheduled_start",
    fields=[
        FieldDef("id", _gen_id, "SERIAL PRIMARY KEY", "integer"),
        FieldDef("work_order_number", _gen_work_order_number, "VARCHAR(50) UNIQUE", "keyword"),
        FieldDef("product_name", fake.catch_phrase, "VARCHAR(255)", "text"),
        FieldDef("product_sku", _gen_sku, "VARCHAR(50)", "keyword"),
        FieldDef("quantity", lambda: fake.random_int(min=1, max=1000), "INTEGER", "integer"),
        FieldDef("unit_of_measure", _gen_unit_of_measure, "VARCHAR(50)", "keyword"),
        FieldDef("scheduled_start", fake.date_time_this_year, "TIMESTAMP", "date"),
        FieldDef("scheduled_end", fake.date_time_this_year, "TIMESTAMP", "date"),
        FieldDef("actual_start", fake.date_time_this_year, "TIMESTAMP", "date", nullable=True),
        FieldDef("actual_end", fake.date_time_this_year, "TIMESTAMP", "date", nullable=True),
        FieldDef("status", _gen_status_manufacturing, "VARCHAR(50)", "keyword"),
        FieldDef("priority", _gen_priority, "VARCHAR(20)", "keyword"),
        FieldDef("assigned_to", fake.name, "VARCHAR(255)", "text"),
        FieldDef("work_center", lambda: f"WC-{fake.random_int(min=1, max=20):02d}", "VARCHAR(50)", "keyword"),
        FieldDef("notes", lambda: fake.text(max_nb_chars=200), "TEXT", "text", nullable=True),
        FieldDef("created_at", fake.date_time_this_year, "TIMESTAMP", "date"),
    ]
)

PRODUCTS = Schema(
    name="products",
    table_name="products",
    description="Product catalog and inventory",
    time_field="created_at",
    fields=[
        FieldDef("id", _gen_id, "SERIAL PRIMARY KEY", "integer"),
        FieldDef("sku", _gen_sku, "VARCHAR(50) UNIQUE", "keyword"),
        FieldDef("name", fake.catch_phrase, "VARCHAR(255)", "text"),
        FieldDef("description", lambda: fake.text(max_nb_chars=500), "TEXT", "text"),
        FieldDef("category", _gen_category, "VARCHAR(100)", "keyword"),
        FieldDef("unit_price", lambda: round(fake.pyfloat(min_value=5, max_value=500, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("cost_price", lambda: round(fake.pyfloat(min_value=2, max_value=300, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("quantity_on_hand", lambda: fake.random_int(min=0, max=1000), "INTEGER", "integer"),
        FieldDef("reorder_level", lambda: fake.random_int(min=5, max=100), "INTEGER", "integer"),
        FieldDef("supplier_name", fake.company, "VARCHAR(255)", "text"),
        FieldDef("supplier_contact", fake.email, "VARCHAR(255)", "keyword"),
        FieldDef("is_active", lambda: fake.boolean(chance_of_getting_true=90), "BOOLEAN", "boolean"),
        FieldDef("created_at", fake.date_time_this_year, "TIMESTAMP", "date"),
        FieldDef("updated_at", fake.date_time_this_year, "TIMESTAMP", "date"),
    ]
)

INVOICES = Schema(
    name="invoices",
    table_name="invoices",
    description="Financial invoices and payments",
    time_field="invoice_date",
    fields=[
        FieldDef("id", _gen_id, "SERIAL PRIMARY KEY", "integer"),
        FieldDef("invoice_number", _gen_invoice_number, "VARCHAR(50) UNIQUE", "keyword"),
        FieldDef("customer_name", fake.name, "VARCHAR(255)", "text"),
        FieldDef("customer_email", fake.email, "VARCHAR(255)", "keyword"),
        FieldDef("invoice_date", fake.date_time_this_year, "TIMESTAMP", "date"),
        FieldDef("due_date", fake.date_time_this_year, "TIMESTAMP", "date"),
        FieldDef("status", _gen_status_invoice, "VARCHAR(50)", "keyword"),
        FieldDef("line_items_json", _gen_line_items_json, "TEXT", "text"),
        FieldDef("subtotal", lambda: round(fake.pyfloat(min_value=50, max_value=5000, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("tax_rate", lambda: round(fake.pyfloat(min_value=0, max_value=0.15, right_digits=4), 4), "DECIMAL(5,4)", "float"),
        FieldDef("tax_amount", lambda: round(fake.pyfloat(min_value=5, max_value=500, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("total", lambda: round(fake.pyfloat(min_value=55, max_value=5500, right_digits=2), 2), "DECIMAL(12,2)", "float"),
        FieldDef("payment_date", fake.date_time_this_year, "TIMESTAMP", "date", nullable=True),
        FieldDef("payment_method", _gen_payment_method, "VARCHAR(50)", "keyword", nullable=True),
        FieldDef("notes", lambda: fake.text(max_nb_chars=200), "TEXT", "text", nullable=True),
        FieldDef("created_at", fake.date_time_this_year, "TIMESTAMP", "date"),
    ]
)


# Registry of all schemas
SCHEMAS: dict[str, Schema] = {
    "contacts": CONTACTS,
    "sales_orders": SALES_ORDERS,
    "manufacturing_orders": MANUFACTURING_ORDERS,
    "products": PRODUCTS,
    "invoices": INVOICES,
}


def get_schema(name: str) -> Schema:
    """Get a schema by name."""
    if name not in SCHEMAS:
        raise ValueError(f"Unknown schema: {name}. Available: {list(SCHEMAS.keys())}")
    return SCHEMAS[name]


def list_schemas() -> list[tuple[str, str]]:
    """Return list of (name, description) for all schemas."""
    return [(name, schema.description) for name, schema in SCHEMAS.items()]
