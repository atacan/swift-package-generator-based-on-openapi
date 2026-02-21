"""Operation 9: Promote misplaced schemas from `components.headers` to `components.schemas`.

Some upstream specs (e.g. DeepL) accidentally place schema definitions under
``components.headers`` while referencing them via ``$ref: '#/components/schemas/Name'``.
The swift-openapi-generator correctly rejects these because the names are absent
from ``components.schemas``.

This transformer detects such misplacements data-driven (no hardcoded names):
1. Scan all ``$ref`` values in the spec for ``#/components/schemas/{name}``.
2. For each ``{name}`` that is missing from ``components.schemas`` but present
   in ``components.headers``, extract the schema and move it into
   ``components.schemas``, removing it from ``components.headers``.

After op7 (fix_header_schemas), the extracted value is always at
``header["schema"]``; the raw header object is used as a fallback.
"""

import json
import re


# Matches $ref values that point to components.schemas
_SCHEMA_REF_RE = re.compile(r'#/components/schemas/([^"]+)')


def _collect_schema_refs(spec: dict) -> set[str]:
    """Return all schema names referenced via ``#/components/schemas/{name}``."""
    raw = json.dumps(spec)
    return set(_SCHEMA_REF_RE.findall(raw))


def promote_misplaced_schemas(spec: dict) -> dict:
    """Move schema definitions from ``components.headers`` to ``components.schemas``.

    A header entry is promoted when:
    - Its name is referenced via ``$ref: '#/components/schemas/{name}'`` somewhere
      in the spec, AND
    - The name is absent from ``components.schemas``.

    The schema value is taken from ``header["schema"]`` (as set by op7) if
    present, otherwise the raw header object is used.

    Args:
        spec: The OpenAPI specification as a dictionary.

    Returns:
        The transformed specification (mutated in-place and returned).
    """
    try:
        headers: dict = spec["components"]["headers"]
    except (KeyError, TypeError):
        return spec

    schemas: dict = spec["components"].setdefault("schemas", {})

    referenced_schema_names = _collect_schema_refs(spec)

    for name in list(headers.keys()):
        if name not in referenced_schema_names:
            continue
        if name in schemas:
            # Already present in schemas — nothing to do.
            continue

        header = headers[name]
        if not isinstance(header, dict):
            continue

        # Prefer the nested schema object added by op7; fall back to raw header.
        schema_value = header.get("schema", header)

        schemas[name] = schema_value
        del headers[name]

    return spec
