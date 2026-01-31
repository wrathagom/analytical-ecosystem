"""Data generation utilities using Faker."""

from datetime import datetime, timedelta
from typing import Iterator, Any
from faker import Faker

from .schemas import Schema, SCHEMAS

fake = Faker()


class DataGenerator:
    """Generates fake data based on schema definitions."""

    def __init__(
        self,
        schema: Schema,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ):
        self.schema = schema
        self.start_date = start_date or (datetime.now() - timedelta(days=365))
        self.end_date = end_date or datetime.now()

    def _generate_time_in_range(self) -> datetime:
        """Generate a random datetime within the configured range."""
        return fake.date_time_between(
            start_date=self.start_date,
            end_date=self.end_date,
        )

    def generate_record(self) -> dict[str, Any]:
        """Generate a single record based on the schema."""
        record = {}

        for field in self.schema.fields:
            # Skip auto-increment id fields
            if field.name == "id" and "SERIAL" in field.sql_type:
                continue

            # Handle time fields specially to respect date range
            if field.name == self.schema.time_field:
                record[field.name] = self._generate_time_in_range()
            elif field.sql_type == "TIMESTAMP":
                # For other timestamp fields, generate relative to the main time field
                if self.schema.time_field in record:
                    base_time = record[self.schema.time_field]
                    # Add some random offset
                    offset_days = fake.random_int(min=0, max=30)
                    record[field.name] = base_time + timedelta(days=offset_days)
                else:
                    record[field.name] = self._generate_time_in_range()
            else:
                # Use the faker function for the field
                value = field.faker_func()
                record[field.name] = value

            # Handle nullable fields randomly
            if field.nullable and fake.random_int(min=1, max=10) <= 2:
                record[field.name] = None

        return record

    def generate_batch(self, count: int) -> list[dict[str, Any]]:
        """Generate a batch of records."""
        return [self.generate_record() for _ in range(count)]

    def generate_batches(
        self,
        total: int,
        batch_size: int = 100,
    ) -> Iterator[list[dict[str, Any]]]:
        """Generate records in batches, yielding each batch."""
        remaining = total
        while remaining > 0:
            current_batch = min(batch_size, remaining)
            yield self.generate_batch(current_batch)
            remaining -= current_batch


def create_generator(
    schema_name: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> DataGenerator:
    """Create a data generator for the specified schema."""
    if schema_name not in SCHEMAS:
        raise ValueError(f"Unknown schema: {schema_name}. Available: {list(SCHEMAS.keys())}")

    return DataGenerator(
        schema=SCHEMAS[schema_name],
        start_date=start_date,
        end_date=end_date,
    )
