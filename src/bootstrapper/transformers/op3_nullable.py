"""Operation 3: Handle nullable properties for Swift OpenAPI Generator.

This transformation detects nullable properties and removes them from the parent's
required array. Swift OpenAPI Generator determines nullability based on whether
a property is in the required array, NOT through nullable: true or type arrays.

This operation:
1. Detects nullable properties (nullable: true, type arrays with null, oneOf/anyOf with null)
2. Removes null-related constructs from schemas
3. Removes nullable properties from parent's required array
"""

from typing import Any

from bootstrapper.transformers.ops_base import recursive_walk


def _is_nullable_property(schema: dict) -> bool:
    """
    Determine if a property schema represents a nullable value.

    Args:
        schema: A property schema object

    Returns:
        True if the property is nullable via any pattern
    """
    if not isinstance(schema, dict):
        return False

    # Pattern 1: OpenAPI 3.0 nullable: true
    if schema.get("nullable") is True:
        return True

    # Pattern 2: OpenAPI 3.1 type array with null
    type_value = schema.get("type")
    if isinstance(type_value, list):
        return "null" in type_value

    # Pattern 3: oneOf/anyOf containing {type: null}
    for key in ["oneOf", "anyOf"]:
        if key in schema and isinstance(schema[key], list):
            for item in schema[key]:
                if isinstance(item, dict) and item.get("type") == "null":
                    return True

    return False


def _clean_null_constructs(schema: dict) -> dict:
    """
    Remove all null-related constructs from a schema.

    Args:
        schema: A property schema object

    Returns:
        The cleaned schema
    """
    if not isinstance(schema, dict):
        return schema

    # Remove nullable: true
    if "nullable" in schema:
        del schema["nullable"]

    # Convert type array [someType, null] back to just someType
    type_value = schema.get("type")
    if isinstance(type_value, list):
        non_null_types = [t for t in type_value if t != "null"]
        if len(non_null_types) == 1:
            schema["type"] = non_null_types[0]
        elif len(non_null_types) > 1:
            schema["type"] = non_null_types
        elif len(non_null_types) == 0:
            # Only null type - keep it as is for now
            pass

    # Remove {type: null} from oneOf/anyOf
    for key in ["oneOf", "anyOf"]:
        if key in schema and isinstance(schema[key], list):
            # Filter out null types
            non_null_items = [
                item
                for item in schema[key]
                if not (isinstance(item, dict) and item.get("type") == "null")
            ]

            # If only one item left, unwrap the oneOf/anyOf
            if len(non_null_items) == 1:
                # Preserve all properties from the single remaining item
                remaining_item = non_null_items[0]
                if isinstance(remaining_item, dict):
                    # Remove the oneOf/anyOf key
                    del schema[key]
                    # Merge properties from the remaining item into schema
                    for prop_key, prop_value in remaining_item.items():
                        if prop_key not in schema:  # Don't overwrite existing properties
                            schema[prop_key] = prop_value
            elif len(non_null_items) > 1:
                # Multiple items remain, keep the oneOf/anyOf
                schema[key] = non_null_items
            else:
                # No items left, remove the key
                del schema[key]

    return schema


def _transform_node(data: Any, parent: Any | None, key_in_parent: str | int | None) -> Any:
    """
    Transform a single node by handling nullable properties.

    This function processes schema objects that have properties and required arrays.
    For each nullable property, it removes the property from the required array.

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
            # Build list of non-nullable property names
            non_nullable_properties = []

            for prop_name in required:
                if prop_name in properties:
                    prop_schema = properties[prop_name]
                    # If property is not nullable, keep it in required
                    if not _is_nullable_property(prop_schema):
                        non_nullable_properties.append(prop_name)

            # Update or remove the required array
            if non_nullable_properties:
                data["required"] = non_nullable_properties
            else:
                # Remove empty required array
                del data["required"]

    # Clean null constructs from all property schemas
    if "properties" in data and isinstance(data["properties"], dict):
        for prop_name, prop_schema in data["properties"].items():
            if isinstance(prop_schema, dict):
                data["properties"][prop_name] = _clean_null_constructs(prop_schema)

    # Also clean null constructs from the current node itself
    # (in case it's a property schema without nested properties)
    if "type" in data or "nullable" in data or "oneOf" in data or "anyOf" in data:
        data = _clean_null_constructs(data)

    return data


def convert_nullable_to_3_1(spec: dict) -> dict:
    """
    Handle nullable properties for Swift OpenAPI Generator compatibility.

    This function:
    1. Detects nullable properties via:
       - nullable: true (OpenAPI 3.0)
       - type: [someType, null] (OpenAPI 3.1 array)
       - oneOf/anyOf with {type: null}
    2. Removes null constructs from schemas
    3. Removes nullable properties from parent's required array

    Swift OpenAPI Generator determines nullability based on the required array,
    not through nullable: true or type arrays. A property NOT in the required
    array is considered optional (nullable) in Swift.

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        The transformed specification

    Example:
        Before (OpenAPI 3.0.0):
        {
            "SpeechToTextModel": {
                "type": "object",
                "required": ["id", "description"],
                "properties": {
                    "id": {"type": "string"},
                    "description": {
                        "type": "string",
                        "nullable": true
                    }
                }
            }
        }

        After:
        {
            "SpeechToTextModel": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"}
                }
            }
        }
    """
    return recursive_walk(spec, _transform_node)
