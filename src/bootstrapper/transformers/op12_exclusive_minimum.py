"""Operation 12: Normalize OpenAPI 3.0 ``exclusiveMinimum`` syntax for 3.1+."""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _is_openapi_3_1_or_later(spec: dict) -> bool:
    """Return whether ``spec`` declares an OpenAPI 3.1+ version."""
    version = spec.get("openapi")
    if not isinstance(version, str):
        return False

    parts = version.split(".")
    if len(parts) < 2:
        return False

    try:
        return int(parts[0]) == 3 and int(parts[1]) >= 1
    except ValueError:
        return False


def _normalize_node(data: Any, parent: Any | None, key_in_parent: str | int | None) -> Any:
    """Convert a 3.0 boolean exclusive minimum into a 3.1 numeric boundary."""
    if not isinstance(data, dict) or data.get("exclusiveMinimum") is not True:
        return data

    minimum = data.get("minimum")
    if not isinstance(minimum, int | float) or isinstance(minimum, bool):
        return data

    data["exclusiveMinimum"] = minimum
    del data["minimum"]
    return data


def normalize_exclusive_minimum(spec: dict) -> dict:
    """Convert 3.0-style boolean exclusive minimums in OpenAPI 3.1+ specs.

    In OpenAPI 3.0, ``minimum: 0`` plus ``exclusiveMinimum: true`` represents
    a value strictly greater than zero. OpenAPI 3.1 instead stores the boundary
    directly as ``exclusiveMinimum: 0``.
    """
    if not _is_openapi_3_1_or_later(spec):
        return spec

    return recursive_walk(spec, _normalize_node)
