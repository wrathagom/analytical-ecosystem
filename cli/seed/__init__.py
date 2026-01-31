"""Seed data module for generating fake data in databases."""

from .schemas import SCHEMAS, get_schema, list_schemas
from .generators import create_generator, DataGenerator
from .backends import get_backend, list_backends, get_seedable_backends
from .normalizer import DataNormalizer
from .ui import seed_data_menu

__all__ = [
    "SCHEMAS",
    "get_schema",
    "list_schemas",
    "create_generator",
    "DataGenerator",
    "get_backend",
    "list_backends",
    "get_seedable_backends",
    "DataNormalizer",
    "seed_data_menu",
]
