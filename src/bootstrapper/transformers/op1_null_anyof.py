"""Operation 1: Remove null from anyOf and oneOf arrays.

This transformation removes type: null entries from anyOf and oneOf arrays,
unwraps anyOf/oneOf when only one type remains, and cleans up default: null
when the type is no longer nullable.
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _process_nullable_array(data: dict, key: str) -> dict:
    """
    Process anyOf or oneOf array by removing null types.

    Args:
        data: The schema object containing the array
        key: Either "anyOf" or "oneOf"

    Returns:
        The transformed schema object
    """
    array_list = data[key]

    # Only process if it's a list
    if not isinstance(array_list, list):
        return data

    # Remove all {type: "null"} entries
    filtered = [
        item for item in array_list if not (isinstance(item, dict) and item.get("type") == "null")
    ]

    # If we didn't remove any null types, return unchanged
    if len(filtered) == len(array_list):
        return data

    # Handle different cases based on filtered results
    if len(filtered) == 0:
        # Edge case: array only had null - keep it as a null type
        return {"type": "null"}
    elif len(filtered) == 1:
        # Unwrap - replace the entire object with the single remaining schema
        unwrapped = filtered[0].copy()
        # Preserve other properties from the parent (like description, example)
        for k, v in data.items():
            if k != key and k not in unwrapped:
                unwrapped[k] = v
        # Remove default: null since type is no longer nullable
        if "default" in unwrapped and unwrapped["default"] is None:
            del unwrapped["default"]
        return unwrapped
    else:
        # Multiple items remain - update the array
        data[key] = filtered
        # Remove default: null since we removed the null type
        if "default" in data and data["default"] is None:
            del data["default"]
        return data


def _transform_node(data: Any, parent: Any | None, key_in_parent: str | int | None) -> Any:
    """
    Transform a single node by processing anyOf and oneOf arrays.

    Args:
        data: The current node being processed
        parent: The parent container of this node
        key_in_parent: The key or index of this node in its parent

    Returns:
        The transformed node
    """
    # Only process dict nodes
    if not isinstance(data, dict):
        return data

    # Process anyOf if present
    if "anyOf" in data:
        data = _process_nullable_array(data, "anyOf")

    # Process oneOf if present
    if "oneOf" in data:
        data = _process_nullable_array(data, "oneOf")

    return data


def remove_null_anyof(spec: dict) -> dict:
    """
    Remove null from anyOf arrays throughout the OpenAPI spec.

    This function:
    1. Removes {type: "null"} from all anyOf arrays
    2. Unwraps anyOf to the single remaining schema if only one item left
    3. Removes default: null when type is no longer nullable

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        The transformed specification with null types removed from anyOf

    Example:
        Before:
        {
            "properties": {
                "name": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ],
                    "default": null
                }
            }
        }

        After:
        {
            "properties": {
                "name": {
                    "type": "string"
                }
            }
        }
    """
    return recursive_walk(spec, _transform_node)
