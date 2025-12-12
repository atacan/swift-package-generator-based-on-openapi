"""Operation 4: Convert format: byte to contentEncoding: base64.

This transformation converts OpenAPI format: byte to contentEncoding: base64
for OpenAPI 3.1+ specs, as required by the updated specification.
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _should_convert_spec(spec: dict) -> bool:
    """
    Determine if the spec should be converted based on OpenAPI version.

    Args:
        spec: The OpenAPI specification

    Returns:
        True if the spec is OpenAPI 3.1+, False otherwise
    """
    version = spec.get("openapi", "3.0.0")

    # Parse version string
    if isinstance(version, str):
        parts = version.split(".")
        if len(parts) >= 2:
            try:
                major = int(parts[0])
                minor = int(parts[1])
                # Only convert for OpenAPI 3.1+
                return major == 3 and minor >= 1
            except ValueError:
                # If parsing fails, default to not converting
                return False

    # If no version or unparseable, don't convert
    return False


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
        Transform a single node by converting format: byte to contentEncoding: base64.

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

        # Check if this is a string type with format: byte
        if data.get("type") == "string" and data.get("format") == "byte":
            # Remove format
            del data["format"]
            # Add contentEncoding
            data["contentEncoding"] = "base64"

        return data

    return _transform_node


def fix_byte_format(spec: dict) -> dict:
    """
    Convert format: byte to contentEncoding: base64 for OpenAPI 3.1+ specs.

    This function:
    1. Checks the OpenAPI version
    2. If version >= 3.1.0:
       - Finds all {type: "string", format: "byte"} occurrences
       - Converts to {type: "string", contentEncoding: "base64"}
       - Removes the 'format' key
    3. If version < 3.1.0, leaves the spec unchanged

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        The transformed specification

    Example:
        Before (OpenAPI 3.1.0):
        {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "File": {
                        "properties": {
                            "data": {
                                "type": "string",
                                "format": "byte"
                            }
                        }
                    }
                }
            }
        }

        After:
        {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "File": {
                        "properties": {
                            "data": {
                                "type": "string",
                                "contentEncoding": "base64"
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
