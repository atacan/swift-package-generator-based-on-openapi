"""Operation 3: Convert nullable to OpenAPI 3.1 format.

This transformation converts OpenAPI 3.0.x nullable: true properties
to OpenAPI 3.1 format using type arrays with null.
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _should_convert_spec(spec: dict) -> bool:
    """
    Determine if the spec should be converted based on OpenAPI version.

    Args:
        spec: The OpenAPI specification

    Returns:
        True if the spec is OpenAPI 3.0.x (or has no version), False otherwise
    """
    version = spec.get("openapi", "3.0.0")

    # Parse version string
    if isinstance(version, str):
        parts = version.split(".")
        if len(parts) >= 2:
            try:
                major = int(parts[0])
                minor = int(parts[1])
                # Only convert for OpenAPI 3.0.x
                return major == 3 and minor == 0
            except ValueError:
                # If parsing fails, default to converting (assume old spec)
                return True

    # If no version or unparseable, assume it needs conversion
    return True


def _make_transform_func(should_convert: bool):
    """
    Create a transform function with the should_convert flag captured.

    Args:
        should_convert: Whether to perform the conversion

    Returns:
        A transform function for use with recursive_walk
    """

    def _transform_node(data: Any, parent: Any | None, key_in_parent: str | int | None) -> Any:
        """
        Transform a single node by converting nullable to type arrays.

        Args:
            data: The current node being processed
            parent: The parent container of this node
            key_in_parent: The key or index of this node in its parent

        Returns:
            The transformed node
        """
        # Skip if we shouldn't convert this spec
        if not should_convert:
            return data

        # Only process dict nodes
        if not isinstance(data, dict):
            return data

        # Process nullable if present
        if "nullable" in data:
            nullable_value = data["nullable"]

            # Remove nullable key
            del data["nullable"]

            # Only convert if nullable was True
            if nullable_value is True and "type" in data:
                current_type = data["type"]

                # Only convert if type is a string (not already an array)
                if isinstance(current_type, str):
                    # Convert to array with null
                    data["type"] = [current_type, "null"]

        return data

    return _transform_node


def convert_nullable_to_3_1(spec: dict) -> dict:
    """
    Convert nullable: true to OpenAPI 3.1 type arrays throughout the spec.

    This function:
    1. Checks the OpenAPI version
    2. If version < 3.1.0 (or missing):
       - Finds all 'nullable: true' occurrences
       - Converts 'type' from string to array [type, "null"]
       - Removes the 'nullable' key
    3. If version >= 3.1.0, leaves the spec unchanged

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        The transformed specification

    Example:
        Before (OpenAPI 3.0.0):
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "properties": {
                            "name": {
                                "type": "string",
                                "nullable": true
                            }
                        }
                    }
                }
            }
        }

        After:
        {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "properties": {
                            "name": {
                                "type": ["string", "null"]
                            }
                        }
                    }
                }
            }
        }
    """
    should_convert = _should_convert_spec(spec)
    transform_func = _make_transform_func(should_convert)
    return recursive_walk(spec, transform_func)
