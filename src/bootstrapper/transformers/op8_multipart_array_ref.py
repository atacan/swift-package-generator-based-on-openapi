"""Operation 8: Fix multipart/form-data properties that are $ref to array schemas.

swift-openapi-generator crashes with:
    preconditionFailure("Array repetition should always use an array schema.")

This happens when a multipart/form-data property uses a $ref that resolves to
a schema of type:array. The generator correctly infers repetitionKind == .array
by following the $ref, but then tries to unwrap the *original* schema (still a
$ref node, not an .array node) and hits the precondition.

Fix: replace the bare $ref with an inline `type: array, items: $ref` schema so
the property schema is directly an array without needing ref resolution.

Before:
    properties:
      additional_formats:
        $ref: '#/components/schemas/AdditionalFormats'   # resolves to type:array

After:
    properties:
      additional_formats:
        type: array
        items:
          $ref: '#/components/schemas/ExportOptions'    # the items from AdditionalFormats
"""

from typing import Any


def _resolve_ref(ref_string: str, spec: dict) -> dict | None:
    """Follow a local JSON $ref like '#/components/schemas/Foo' to its target."""
    if not ref_string.startswith("#/"):
        return None  # external refs are not our responsibility
    parts = ref_string.lstrip("#/").split("/")
    node: Any = spec
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, dict) else None


def _is_array_schema(schema: dict, spec: dict, _seen: frozenset[str] = frozenset()) -> bool:
    """Return True if schema ultimately resolves to type:array (follows $refs once)."""
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in _seen:
            return False
        resolved = _resolve_ref(ref, spec)
        if resolved is None:
            return False
        return _is_array_schema(resolved, spec, _seen | {ref})
    return schema.get("type") == "array"


def _inline_array(prop_schema: dict, spec: dict) -> dict:
    """
    Given a property schema that is a $ref to an array schema, return an
    equivalent inline array schema: {type: array, items: <original items>}.

    Follows $ref chains until it finds the actual array schema.
    """
    current = prop_schema
    seen: set[str] = set()
    while "$ref" in current:
        ref = current["$ref"]
        if ref in seen:
            return prop_schema  # cycle guard, return unchanged
        seen.add(ref)
        resolved = _resolve_ref(ref, spec)
        if resolved is None:
            return prop_schema
        current = resolved

    # current is now the array schema
    items = current.get("items", {})
    inlined: dict = {"type": "array", "items": items}
    # Preserve description if present in the ref'd schema
    if "description" in current:
        inlined["description"] = current["description"]
    return inlined


def _fix_multipart_schema_properties(schema: dict, spec: dict) -> None:
    """Mutate a multipart object schema, inlining any $ref-to-array properties."""
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return
    for prop_name, prop_schema in list(properties.items()):
        if not isinstance(prop_schema, dict):
            continue
        if "$ref" in prop_schema and _is_array_schema(prop_schema, spec):
            properties[prop_name] = _inline_array(prop_schema, spec)


def _resolve_schema_node(schema_node: dict | None, spec: dict) -> dict | None:
    """Dereference a top-level schema $ref if present."""
    if schema_node is None:
        return None
    if "$ref" in schema_node:
        return _resolve_ref(schema_node["$ref"], spec)
    return schema_node


def _process_content_map(content: dict, spec: dict) -> None:
    """Fix multipart properties in a content map (from requestBody.content)."""
    for content_type, content_value in content.items():
        if "multipart" not in content_type:
            continue
        if not isinstance(content_value, dict):
            continue
        raw_schema = content_value.get("schema")
        schema = _resolve_schema_node(raw_schema, spec)
        if isinstance(schema, dict):
            _fix_multipart_schema_properties(schema, spec)


def fix_multipart_array_refs(spec: dict) -> dict:
    """
    Fix multipart/form-data properties that are bare $refs to array schemas.

    Scans paths.*.*.requestBody and components.requestBodies for
    multipart/form-data content, then replaces any property whose schema is a
    $ref resolving to type:array with an equivalent inline array schema.

    Args:
        spec: The OpenAPI specification as a dictionary (mutated in place and returned)

    Returns:
        The transformed specification

    Example:
        Before:
        {
          "properties": {
            "additional_formats": {"$ref": "#/components/schemas/AdditionalFormats"}
          }
        }
        where AdditionalFormats = {"type": "array", "items": {"$ref": "...ExportOptions"}}

        After:
        {
          "properties": {
            "additional_formats": {
              "type": "array",
              "items": {"$ref": "#/components/schemas/ExportOptions"}
            }
          }
        }
    """
    paths = spec.get("paths", {})
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "put", "post", "delete", "options", "head", "patch", "trace"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            request_body = operation.get("requestBody", {})
            if "$ref" in request_body:
                request_body = _resolve_ref(request_body["$ref"], spec) or {}
            content = request_body.get("content", {})
            if isinstance(content, dict):
                _process_content_map(content, spec)

    components = spec.get("components", {})
    for rb_value in components.get("requestBodies", {}).values():
        if not isinstance(rb_value, dict):
            continue
        content = rb_value.get("content", {})
        if isinstance(content, dict):
            _process_content_map(content, spec)

    return spec
