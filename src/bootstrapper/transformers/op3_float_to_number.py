"""Operation 3: Convert type: float to type: number.

This transformation converts invalid OpenAPI 'float' types to the correct
'number' type with 'format: float' annotation.

Invalid OpenAPI:
    type: float

Valid OpenAPI:
    type: number
    format: float
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _transform_node(data: Any, parent: Any | None, key_in_parent: str | int | None) -> Any:
    """Transform a single node by converting float to number.

    Args:
        data: Current node in the OpenAPI spec
        parent: Parent container (dict or list)
        key_in_parent: Key or index in parent

    Returns:
        Transformed node
    """
    if not isinstance(data, dict):
        return data

    # Check if type is "float" (invalid)
    if data.get("type") == "float":
        data["type"] = "number"
        data["format"] = "float"

    return data


def convert_float_to_number(spec: dict) -> dict:
    """Convert all 'float' types to 'number' with format annotation.

    Recursively traverses the entire OpenAPI specification and converts
    any invalid 'type: float' to 'type: number' with 'format: float'.

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        The transformed specification with all float types corrected
    """
    return recursive_walk(spec, _transform_node)
