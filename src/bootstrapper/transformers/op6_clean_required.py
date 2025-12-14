"""Operation 5: Clean required arrays to match properties.

This transformation filters the 'required' array to only include properties
that actually exist in the 'properties' object, preventing validation errors
from invalid required property references.
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _transform_node(data: Any, parent: Any | None, key_in_parent: str | int | None) -> Any:
    """
    Transform a single node by cleaning the required array.

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

    # Check if this node has both properties and required
    if "properties" in data and "required" in data:
        properties = data["properties"]
        required = data["required"]

        # Only process if properties is a dict and required is a list
        if isinstance(properties, dict) and isinstance(required, list):
            # Filter required to only include keys that exist in properties
            filtered_required = [key for key in required if key in properties]

            # Update or remove the required array
            if filtered_required:
                data["required"] = filtered_required
            else:
                # Remove empty required array
                del data["required"]

    # Also handle case where there's required but no properties
    elif "required" in data and "properties" not in data:
        # If there are no properties defined, required doesn't make sense
        if isinstance(data.get("required"), list):
            del data["required"]

    return data


def clean_required_arrays(spec: dict) -> dict:
    """
    Clean all 'required' arrays to only include existing properties.

    This function:
    1. Finds all schema objects with both 'properties' and 'required'
    2. Filters the 'required' array to only include keys present in 'properties'
    3. Removes empty 'required' arrays
    4. Removes 'required' arrays when there are no 'properties'

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        The transformed specification with cleaned required arrays

    Example:
        Before:
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
            },
            "required": ["name", "email", "phone", "address"]
        }

        After:
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
            },
            "required": ["name", "email"]
        }
    """
    return recursive_walk(spec, _transform_node)
