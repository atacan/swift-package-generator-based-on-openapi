"""Remove selected fields recursively from OpenAPI specifications."""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk

# Add field names here to omit them throughout the transformed specification.
FIELDS_TO_REMOVE = frozenset({"x-codeSamples"})


def _remove_fields(data: Any, parent: Any, key: str | int | None) -> Any:
    if isinstance(data, dict):
        for field in FIELDS_TO_REMOVE:
            data.pop(field, None)
    return data


def remove_fields(spec: dict) -> dict:
    """Remove FIELDS_TO_REMOVE recursively while preserving other fields."""
    return recursive_walk(spec, _remove_fields)
