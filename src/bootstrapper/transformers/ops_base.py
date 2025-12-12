"""Base utilities for OpenAPI transformation operations."""

from collections.abc import Callable
from typing import Any


def recursive_walk(
    data: Any,
    transform_func: Callable[[Any, Any | None, str | int | None], Any],
    parent: Any | None = None,
    key_in_parent: str | int | None = None,
) -> Any:
    """
    Recursively traverse a nested dict/list structure and apply transformations.

    This function walks through all nodes in a JSON-like data structure
    (dicts and lists), applying the transform_func at each node. The
    transform_func can modify the data in-place and should return the
    (potentially modified) data.

    Args:
        data: The current node being processed (can be dict, list, or scalar)
        transform_func: A callable that takes (data, parent, key_in_parent)
                       and returns the transformed data
        parent: The parent container (dict or list) of the current node
        key_in_parent: The key (str for dict) or index (int for list) of
                      this node in its parent

    Returns:
        The transformed data (same type as input, but potentially modified)

    Example:
        def uppercase_strings(data, parent, key):
            if isinstance(data, str):
                return data.upper()
            return data

        result = recursive_walk({"name": "john"}, uppercase_strings)
        # Result: {"name": "JOHN"}
    """
    # Apply transformation to current node
    data = transform_func(data, parent, key_in_parent)

    if isinstance(data, dict):
        # We must list keys because the loop might modify the dict
        for k in list(data.keys()):
            data[k] = recursive_walk(data[k], transform_func, parent=data, key_in_parent=k)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            data[i] = recursive_walk(item, transform_func, parent=data, key_in_parent=i)

    return data
