"""Operation 1: Remove null from anyOf arrays.

This transformation removes type: null entries from anyOf arrays,
unwraps anyOf when only one type remains, and cleans up default: null
when the type is no longer nullable.
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _transform_node(data: Any, parent: Any | None, key_in_parent: str | int | None) -> Any:
    """
    Transform a single node by processing anyOf arrays.

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
        any_of_list = data["anyOf"]

        # Only process if it's a list
        if isinstance(any_of_list, list):
            # Remove all {type: "null"} entries
            filtered = [
                item for item in any_of_list
                if not (isinstance(item, dict) and item.get("type") == "null")
            ]

            # If we removed null types, update the anyOf
            if len(filtered) != len(any_of_list):
                if len(filtered) == 0:
                    # Edge case: anyOf only had null - keep it as a null type
                    data = {"type": "null"}
                elif len(filtered) == 1:
                    # Unwrap anyOf - replace the entire object with the single remaining schema
                    unwrapped = filtered[0].copy()
                    # Preserve other properties from the parent (like description, example)
                    for key, value in data.items():
                        if key != "anyOf" and key not in unwrapped:
                            unwrapped[key] = value
                    data = unwrapped
                    # Remove default: null since type is no longer nullable
                    if "default" in data and data["default"] is None:
                        del data["default"]
                else:
                    # Multiple items remain - update anyOf list
                    data["anyOf"] = filtered
                    # Remove default: null since we removed the null type
                    if "default" in data and data["default"] is None:
                        del data["default"]

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
