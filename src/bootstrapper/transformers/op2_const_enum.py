"""Operation 2: Convert const to enum.

This transformation converts OpenAPI 'const' keywords to 'enum' arrays
with a single value, which is required for Swift OpenAPIGenerator compatibility.
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _transform_node(data: Any, parent: Any | None, key_in_parent: str | int | None) -> Any:
    """
    Transform a single node by converting const to enum.

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

    # Process const if present
    if "const" in data:
        const_value = data["const"]
        # Remove const
        del data["const"]
        # Add enum with single value
        data["enum"] = [const_value]

    return data


def convert_const_to_enum(spec: dict) -> dict:
    """
    Convert all 'const' keywords to 'enum' arrays throughout the OpenAPI spec.

    This function:
    1. Finds all 'const' keys in the specification
    2. Captures the const value
    3. Removes the 'const' key
    4. Adds an 'enum' key with an array containing the const value

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        The transformed specification with const converted to enum

    Example:
        Before:
        {
            "properties": {
                "status": {
                    "type": "string",
                    "const": "active"
                }
            }
        }

        After:
        {
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active"]
                }
            }
        }
    """
    return recursive_walk(spec, _transform_node)
