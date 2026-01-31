"""Tests for the seed data module."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class TestSchemas:
    """Tests for schema definitions."""

    def test_all_schemas_exist(self):
        from cli.seed.schemas import SCHEMAS

        expected = ["contacts", "sales_orders", "manufacturing_orders", "products", "invoices"]
        assert list(SCHEMAS.keys()) == expected

    def test_list_schemas(self):
        from cli.seed.schemas import list_schemas

        schemas = list_schemas()
        assert len(schemas) == 5
        assert all(isinstance(s, tuple) and len(s) == 2 for s in schemas)
        # Check format is (name, description)
        names = [s[0] for s in schemas]
        assert "contacts" in names
        assert "sales_orders" in names

    def test_get_schema_valid(self):
        from cli.seed.schemas import get_schema

        schema = get_schema("contacts")
        assert schema.name == "contacts"
        assert schema.table_name == "contacts"
        assert schema.time_field == "created_at"
        assert len(schema.fields) > 0

    def test_get_schema_invalid(self):
        from cli.seed.schemas import get_schema

        with pytest.raises(ValueError, match="Unknown schema"):
            get_schema("nonexistent")

    def test_contacts_schema_fields(self):
        from cli.seed.schemas import CONTACTS

        field_names = CONTACTS.get_field_names()
        assert "id" in field_names
        assert "first_name" in field_names
        assert "email" in field_names
        assert "created_at" in field_names

    def test_sales_orders_schema_fields(self):
        from cli.seed.schemas import SALES_ORDERS

        field_names = SALES_ORDERS.get_field_names()
        assert "order_number" in field_names
        assert "customer_name" in field_names
        assert "order_date" in field_names
        assert "total" in field_names

    def test_manufacturing_orders_schema_fields(self):
        from cli.seed.schemas import MANUFACTURING_ORDERS

        field_names = MANUFACTURING_ORDERS.get_field_names()
        assert "work_order_number" in field_names
        assert "product_name" in field_names
        assert "scheduled_start" in field_names

    def test_products_schema_fields(self):
        from cli.seed.schemas import PRODUCTS

        field_names = PRODUCTS.get_field_names()
        assert "sku" in field_names
        assert "name" in field_names
        assert "unit_price" in field_names
        assert "quantity_on_hand" in field_names

    def test_invoices_schema_fields(self):
        from cli.seed.schemas import INVOICES

        field_names = INVOICES.get_field_names()
        assert "invoice_number" in field_names
        assert "invoice_date" in field_names
        assert "line_items_json" in field_names
        assert "total" in field_names

    def test_schema_sql_columns(self):
        from cli.seed.schemas import CONTACTS

        columns = CONTACTS.get_sql_columns()
        assert len(columns) > 0
        # Each column should be (name, type) tuple
        assert all(isinstance(c, tuple) and len(c) == 2 for c in columns)

    def test_schema_es_mapping(self):
        from cli.seed.schemas import CONTACTS

        mapping = CONTACTS.get_es_mapping()
        assert "mappings" in mapping
        assert "properties" in mapping["mappings"]
        props = mapping["mappings"]["properties"]
        assert "email" in props
        assert "created_at" in props


class TestGenerators:
    """Tests for data generators."""

    def test_create_generator(self):
        from cli.seed.generators import create_generator

        gen = create_generator("contacts")
        assert gen.schema.name == "contacts"

    def test_create_generator_invalid_schema(self):
        from cli.seed.generators import create_generator

        with pytest.raises(ValueError, match="Unknown schema"):
            create_generator("nonexistent")

    def test_generate_single_record(self):
        from cli.seed.generators import create_generator

        gen = create_generator("contacts")
        record = gen.generate_record()

        assert isinstance(record, dict)
        assert "first_name" in record
        assert "last_name" in record
        assert "email" in record
        assert "created_at" in record
        # id should not be in record (auto-generated)
        assert "id" not in record

    def test_generate_batch(self):
        from cli.seed.generators import create_generator

        gen = create_generator("contacts")
        records = gen.generate_batch(10)

        assert len(records) == 10
        assert all(isinstance(r, dict) for r in records)

    def test_generate_batches_iterator(self):
        from cli.seed.generators import create_generator

        gen = create_generator("contacts")
        batches = list(gen.generate_batches(25, batch_size=10))

        assert len(batches) == 3  # 10 + 10 + 5
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5

    def test_date_range_respected(self):
        from cli.seed.generators import create_generator

        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        gen = create_generator("contacts", start_date=start, end_date=end)

        for _ in range(20):
            record = gen.generate_record()
            created_at = record["created_at"]
            assert start <= created_at <= end + timedelta(days=30)  # Allow some offset for related dates

    @pytest.mark.parametrize("schema_name", [
        "contacts",
        "sales_orders",
        "manufacturing_orders",
        "products",
        "invoices",
    ])
    def test_all_schemas_generate_valid_records(self, schema_name):
        from cli.seed.generators import create_generator

        gen = create_generator(schema_name)
        record = gen.generate_record()

        assert isinstance(record, dict)
        assert len(record) > 0


class TestNormalizer:
    """Tests for data normalization."""

    def test_normalizer_init(self):
        from cli.seed.normalizer import DataNormalizer

        norm = DataNormalizer()
        assert len(norm.customers) == 0
        assert len(norm.products) == 0

    def test_extract_customer_from_sales_order(self):
        from cli.seed.normalizer import DataNormalizer

        norm = DataNormalizer()
        record = {
            "order_number": "ORD-12345",
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "customer_phone": "555-1234",
            "total": 100.00,
        }

        normalized = norm.normalize_record(record, "sales_orders")

        # Should have customer_id instead of customer fields
        assert "customer_id" in normalized
        assert "customer_name" not in normalized
        assert "customer_email" not in normalized
        assert "total" in normalized  # Non-customer fields preserved

        # Customer should be extracted
        customers = norm.get_customers_table()
        assert len(customers) == 1
        assert customers[0]["email"] == "john@example.com"

    def test_same_customer_reused(self):
        from cli.seed.normalizer import DataNormalizer

        norm = DataNormalizer()

        record1 = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "customer_phone": "555-1234",
        }
        record2 = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "customer_phone": "555-1234",
        }

        norm1 = norm.normalize_record(record1, "sales_orders")
        norm2 = norm.normalize_record(record2, "sales_orders")

        # Should have same customer_id
        assert norm1["customer_id"] == norm2["customer_id"]

        # Only one customer should exist
        customers = norm.get_customers_table()
        assert len(customers) == 1

    def test_extract_product_from_manufacturing_order(self):
        from cli.seed.normalizer import DataNormalizer

        norm = DataNormalizer()
        record = {
            "work_order_number": "WO-12345",
            "product_name": "Widget",
            "product_sku": "SKU-123",
            "quantity": 100,
        }

        normalized = norm.normalize_record(record, "manufacturing_orders")

        assert "product_id" in normalized
        assert "product_name" not in normalized
        assert "product_sku" not in normalized
        assert "quantity" in normalized

        products = norm.get_products_table()
        assert len(products) == 1
        assert products[0]["sku"] == "SKU-123"

    def test_reset_normalizer(self):
        from cli.seed.normalizer import DataNormalizer

        norm = DataNormalizer()
        norm.normalize_record({
            "customer_email": "test@example.com",
            "customer_name": "Test",
        }, "sales_orders")

        assert len(norm.get_customers_table()) == 1

        norm.reset()

        assert len(norm.get_customers_table()) == 0
        assert len(norm.get_products_table()) == 0

    def test_contacts_not_normalized(self):
        from cli.seed.normalizer import DataNormalizer

        norm = DataNormalizer()
        record = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }

        normalized = norm.normalize_record(record, "contacts")

        # Contacts should pass through unchanged
        assert normalized == record


class TestBackendRegistry:
    """Tests for backend registry and factory."""

    def test_list_backends(self):
        from cli.seed.backends import list_backends

        backends = list_backends()
        assert len(backends) == 3

        names = [b[0] for b in backends]
        assert "postgres" in names
        assert "mysql" in names
        assert "elasticsearch" in names

    def test_get_seedable_backends(self):
        from cli.seed.backends import get_seedable_backends

        backends = get_seedable_backends()
        assert "postgres" in backends
        assert "mysql" in backends
        assert "elasticsearch" in backends

    def test_get_backend_postgres(self):
        from cli.seed.backends import get_backend
        from cli.seed.backends.postgres import PostgresBackend

        backend = get_backend("postgres")
        assert isinstance(backend, PostgresBackend)

    def test_get_backend_mysql(self):
        from cli.seed.backends import get_backend
        from cli.seed.backends.mysql import MySQLBackend

        backend = get_backend("mysql")
        assert isinstance(backend, MySQLBackend)

    def test_get_backend_elasticsearch(self):
        from cli.seed.backends import get_backend
        from cli.seed.backends.elasticsearch import ElasticsearchBackend

        backend = get_backend("elasticsearch")
        assert isinstance(backend, ElasticsearchBackend)

    def test_get_backend_alias(self):
        from cli.seed.backends import get_backend
        from cli.seed.backends.postgres import PostgresBackend

        backend = get_backend("pg")
        assert isinstance(backend, PostgresBackend)

    def test_get_backend_invalid(self):
        from cli.seed.backends import get_backend

        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend("nonexistent")


class TestPostgresBackend:
    """Tests for PostgreSQL backend."""

    def test_default_connection_params(self):
        from cli.seed.backends.postgres import PostgresBackend

        backend = PostgresBackend()
        assert backend.host == "localhost"
        assert backend.port == 5432
        assert backend.user == "analyticsUser"
        assert backend.database == "analytics"

    def test_custom_connection_params(self):
        from cli.seed.backends.postgres import PostgresBackend

        backend = PostgresBackend(
            host="db.example.com",
            port=5433,
            user="custom_user",
            password="custom_pass",
            database="custom_db",
        )
        assert backend.host == "db.example.com"
        assert backend.port == 5433
        assert backend.user == "custom_user"

    def test_supports_normalization(self):
        from cli.seed.backends.postgres import PostgresBackend

        backend = PostgresBackend()
        assert backend.supports_normalization is True

    def test_get_connection_info(self):
        from cli.seed.backends.postgres import PostgresBackend

        backend = PostgresBackend()
        info = backend.get_connection_info()

        assert "host" in info
        assert "port" in info
        assert "user" in info
        assert "password" in info
        assert "database" in info
        assert "connect_cmd" in info
        assert "psql" in info["connect_cmd"]


class TestMySQLBackend:
    """Tests for MySQL backend."""

    def test_default_connection_params(self):
        from cli.seed.backends.mysql import MySQLBackend

        backend = MySQLBackend()
        assert backend.host == "localhost"
        assert backend.port == 3306
        assert backend.user == "analyticsUser"
        assert backend.database == "analytics"

    def test_supports_normalization(self):
        from cli.seed.backends.mysql import MySQLBackend

        backend = MySQLBackend()
        assert backend.supports_normalization is True

    def test_get_connection_info(self):
        from cli.seed.backends.mysql import MySQLBackend

        backend = MySQLBackend()
        info = backend.get_connection_info()

        assert "host" in info
        assert "database" in info
        assert "connect_cmd" in info
        assert "mysql" in info["connect_cmd"]


class TestElasticsearchBackend:
    """Tests for Elasticsearch backend."""

    def test_default_connection_params(self):
        from cli.seed.backends.elasticsearch import ElasticsearchBackend

        backend = ElasticsearchBackend()
        assert backend.host == "localhost"
        assert backend.port == 9200

    def test_does_not_support_normalization(self):
        from cli.seed.backends.elasticsearch import ElasticsearchBackend

        backend = ElasticsearchBackend()
        assert backend.supports_normalization is False

    def test_get_connection_info(self):
        from cli.seed.backends.elasticsearch import ElasticsearchBackend

        backend = ElasticsearchBackend()
        info = backend.get_connection_info()

        assert "host" in info
        assert "port" in info
        assert "url" in info
        assert "connect_cmd" in info
        assert "curl" in info["connect_cmd"]


class TestCmdSeed:
    """Tests for the cmd_seed command."""

    def test_invalid_data_type(self, capsys):
        from cli.commands import cmd_seed

        args = SimpleNamespace(
            db="postgres",
            type="invalid_type",
            count=10,
            batch_size=10,
            normalize=False,
            start=None,
            end=None,
        )

        result = cmd_seed(args)
        assert result is False

        out = capsys.readouterr().out
        assert "Invalid data type" in out

    def test_invalid_start_date(self, capsys):
        from cli.commands import cmd_seed

        args = SimpleNamespace(
            db="postgres",
            type="contacts",
            count=10,
            batch_size=10,
            normalize=False,
            start="not-a-date",
            end=None,
        )

        result = cmd_seed(args)
        assert result is False

        out = capsys.readouterr().out
        assert "Invalid start date" in out

    def test_invalid_end_date(self, capsys):
        from cli.commands import cmd_seed

        args = SimpleNamespace(
            db="postgres",
            type="contacts",
            count=10,
            batch_size=10,
            normalize=False,
            start=None,
            end="not-a-date",
        )

        result = cmd_seed(args)
        assert result is False

        out = capsys.readouterr().out
        assert "Invalid end date" in out

    def test_normalization_disabled_for_elasticsearch(self, capsys, monkeypatch):
        from cli.seed.backends.elasticsearch import ElasticsearchBackend
        import cli.seed as seed_module

        # Mock the backend to avoid actual connection
        mock_backend = MagicMock(spec=ElasticsearchBackend)
        mock_backend.supports_normalization = False
        mock_backend.get_connection_info.return_value = {}

        def mock_get_backend(name):
            return mock_backend

        monkeypatch.setattr(seed_module, "get_backend", mock_get_backend)

        from cli.commands import cmd_seed

        args = SimpleNamespace(
            db="elasticsearch",
            type="contacts",
            count=10,
            batch_size=10,
            normalize=True,  # Requesting normalization
            start=None,
            end=None,
        )

        # Will fail at connection, but should print warning first
        cmd_seed(args)

        out = capsys.readouterr().out
        assert "Normalization not supported" in out


class TestIntegration:
    """Integration tests that require running databases."""

    def test_full_seed_workflow_mocked(self, capsys, monkeypatch):
        """Test the full seeding workflow with mocked backend."""
        from cli.seed.backends.postgres import PostgresBackend
        import cli.seed as seed_module

        mock_backend = MagicMock(spec=PostgresBackend)
        mock_backend.name = "postgres"
        mock_backend.supports_normalization = True
        mock_backend.get_connection_info.return_value = {
            "host": "localhost",
            "port": "5432",
            "user": "test",
            "password": "test",
            "database": "test",
            "connect_cmd": "psql -h localhost -U test -d test",
        }
        mock_backend.get_count.return_value = 100
        mock_backend.insert_batch.return_value = 100

        def mock_get_backend(name):
            return mock_backend

        monkeypatch.setattr(seed_module, "get_backend", mock_get_backend)

        from cli.commands import cmd_seed

        args = SimpleNamespace(
            db="postgres",
            type="contacts",
            count=100,
            batch_size=50,
            normalize=False,
            start="2024-01-01",
            end="2024-12-31",
        )

        result = cmd_seed(args)

        assert result is True

        # Verify backend methods were called
        mock_backend.connect.assert_called()
        mock_backend.create_table.assert_called()
        mock_backend.insert_batch.assert_called()
        mock_backend.disconnect.assert_called()

        out = capsys.readouterr().out
        assert "Inserted" in out
        assert "Connection info" in out

    @pytest.mark.parametrize("schema_name", [
        "contacts",
        "sales_orders",
        "manufacturing_orders",
        "products",
        "invoices",
    ])
    def test_seed_all_schemas_mocked(self, schema_name, capsys, monkeypatch):
        """Test seeding all schema types with mocked backend."""
        from cli.seed.backends.postgres import PostgresBackend
        import cli.seed as seed_module

        mock_backend = MagicMock(spec=PostgresBackend)
        mock_backend.name = "postgres"
        mock_backend.supports_normalization = True
        mock_backend.get_connection_info.return_value = {}
        mock_backend.get_count.return_value = 10
        mock_backend.insert_batch.return_value = 10

        def mock_get_backend(name):
            return mock_backend

        monkeypatch.setattr(seed_module, "get_backend", mock_get_backend)

        from cli.commands import cmd_seed

        args = SimpleNamespace(
            db="postgres",
            type=schema_name,
            count=10,
            batch_size=10,
            normalize=False,
            start=None,
            end=None,
        )

        result = cmd_seed(args)
        assert result is True
