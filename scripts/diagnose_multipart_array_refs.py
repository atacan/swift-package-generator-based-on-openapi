"""
Diagnose multipart/form-data properties that are $ref to array schemas.

These cause a preconditionFailure in swift-openapi-generator:
    FileTranslator.parseMultipartPartInfo — "Array repetition should always use an array schema."

Root cause: the generator correctly detects repetitionKind == .array by following the $ref,
but then tries to unwrap the *original* schema (still a $ref, not .array) and crashes.

Usage:
    uv run python scripts/diagnose_multipart_array_refs.py path/to/openapi.yaml
"""

import json
import sys
from pathlib import Path

import yaml


def load_spec(path: Path) -> dict:
    suffix = path.suffix.lower()
    with open(path, encoding="utf-8") as f:
        if suffix == ".json":
            return json.load(f)
        elif suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported extension: {suffix}")


def resolve_ref(ref_string: str, spec: dict) -> dict | None:
    """Follow a JSON $ref like '#/components/schemas/Foo' to its target dict."""
    if not ref_string.startswith("#/"):
        return None  # External refs — skip
    parts = ref_string.lstrip("#/").split("/")
    node = spec
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def is_array_schema(schema: dict, spec: dict, _seen: set[str] | None = None) -> bool:
    """
    Return True if schema ultimately resolves to type:array.
    Follows $ref chains up to one level to avoid infinite loops.
    """
    if _seen is None:
        _seen = set()

    if not isinstance(schema, dict):
        return False

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in _seen:
            return False
        _seen.add(ref)
        resolved = resolve_ref(ref, spec)
        if resolved is None:
            return False
        return is_array_schema(resolved, spec, _seen)

    return schema.get("type") == "array"


def resolve_schema_for_multipart(schema_or_ref: dict | None, spec: dict) -> dict | None:
    """
    Given the schema field of a multipart/form-data content entry,
    resolve any top-level $ref and return the object schema.
    """
    if schema_or_ref is None:
        return None
    if "$ref" in schema_or_ref:
        return resolve_ref(schema_or_ref["$ref"], spec)
    return schema_or_ref


def find_multipart_array_ref_problems(spec: dict) -> list[dict]:
    """
    Find all multipart/form-data properties that are $ref to array schemas.

    Returns a list of finding dicts with keys:
        location   — human-readable path (method + path + property name)
        property   — property name
        ref        — the $ref string
        resolved   — the resolved schema (type: array + items)
    """
    problems = []

    paths = spec.get("paths", {})
    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "put", "post", "delete", "options", "head", "patch", "trace"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue

            request_body = operation.get("requestBody", {})
            # Dereference requestBody $ref if needed
            if "$ref" in request_body:
                request_body = resolve_ref(request_body["$ref"], spec) or {}

            content = request_body.get("content", {})
            for content_type, content_value in content.items():
                if "multipart" not in content_type:
                    continue

                raw_schema = content_value.get("schema")
                schema = resolve_schema_for_multipart(raw_schema, spec)
                if not isinstance(schema, dict):
                    continue

                properties = schema.get("properties", {})
                for prop_name, prop_schema in properties.items():
                    if not isinstance(prop_schema, dict):
                        continue

                    # A $ref that resolves to an array — this is the crash case
                    if "$ref" in prop_schema and is_array_schema(prop_schema, spec):
                        resolved = resolve_ref(prop_schema["$ref"], spec)
                        problems.append(
                            {
                                "location": f"{method.upper()} {path_str}  (content-type: {content_type})",
                                "property": prop_name,
                                "ref": prop_schema["$ref"],
                                "resolved_type": resolved.get("type") if resolved else "unknown",
                                "resolved_items": resolved.get("items") if resolved else None,
                            }
                        )

    # Also check components/requestBodies
    components = spec.get("components", {})
    for rb_name, rb_value in components.get("requestBodies", {}).items():
        if not isinstance(rb_value, dict):
            continue
        content = rb_value.get("content", {})
        for content_type, content_value in content.items():
            if "multipart" not in content_type:
                continue
            raw_schema = content_value.get("schema")
            schema = resolve_schema_for_multipart(raw_schema, spec)
            if not isinstance(schema, dict):
                continue
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                if not isinstance(prop_schema, dict):
                    continue
                if "$ref" in prop_schema and is_array_schema(prop_schema, spec):
                    resolved = resolve_ref(prop_schema["$ref"], spec)
                    problems.append(
                        {
                            "location": f"components/requestBodies/{rb_name}  (content-type: {content_type})",
                            "property": prop_name,
                            "ref": prop_schema["$ref"],
                            "resolved_type": resolved.get("type") if resolved else "unknown",
                            "resolved_items": resolved.get("items") if resolved else None,
                        }
                    )

    return problems


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/diagnose_multipart_array_refs.py <openapi_file>")
        sys.exit(1)

    spec_path = Path(sys.argv[1])
    if not spec_path.exists():
        print(f"File not found: {spec_path}")
        sys.exit(1)

    spec = load_spec(spec_path)
    problems = find_multipart_array_ref_problems(spec)

    if not problems:
        print("No multipart $ref-to-array problems found.")
        return

    print(f"Found {len(problems)} multipart $ref-to-array problem(s):\n")
    for i, p in enumerate(problems, 1):
        print(f"  [{i}] {p['location']}")
        print(f"       property : {p['property']}")
        print(f"       $ref     : {p['ref']}")
        print(f"       resolves : type={p['resolved_type']}, items={p['resolved_items']}")
        print()

    print(
        "Fix: replace each $ref-to-array property with an inline 'type: array, items: $ref' schema,\n"
        "or apply the op8_multipart_array_ref transformer.\n"
    )


if __name__ == "__main__":
    main()
