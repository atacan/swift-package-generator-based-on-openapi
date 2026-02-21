"""Operation 7: Fix Header Objects missing `schema` wrapper.

This transformation fixes two issues in `components.headers`:

1. Headers where schema properties (type, enum, etc.) are placed directly
   on the Header Object instead of inside a nested `schema` key.
2. Headers whose value is null, which are removed entirely.
"""

# Pure schema keys — only valid inside a Schema Object, never on a Header Object.
# When found on a bare header, they must be moved into a `schema` sub-object.
_PURE_SCHEMA_KEYS = {
    "type",
    "properties",
    "items",
    "enum",
    "format",
    "default",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "pattern",
    "additionalProperties",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "title",
    "readOnly",
    "writeOnly",
    "nullable",
    "discriminator",
    "xml",
    "externalDocs",
}

# Dual-purpose keys — valid on both the Header Object and a Schema Object.
# These are kept at the top level AND copied into `schema`.
_DUAL_KEYS = {"description", "example", "examples"}

# `required` is special: on a Header Object it is a *boolean* ("is this header
# required?"), but inside a Schema Object it is a *list* of required property
# names.  We detect which interpretation applies by checking the value type.
#
# Keys valid only at the Header Object level (never moved):
_HEADER_ONLY_KEYS = {
    "deprecated",
    "allowEmptyValue",
    "style",
    "explode",
    "allowReserved",
    "schema",
    "content",
}


def fix_header_schemas(spec: dict) -> dict:
    """Wrap bare schema keys in `components.headers` into a `schema` sub-object.

    For each header in ``spec["components"]["headers"]``:

    - If the header value is **null**, remove it from the map.
    - If the header has neither ``schema`` nor ``content`` keys but does have
      schema-level keys (``type``, ``properties``, ``enum``, …), move those
      keys into a new ``schema`` sub-object.  ``description`` and ``example``
      are kept at the header level *and* copied into ``schema``.

    Only ``components.headers`` is touched; inline headers inside response
    objects are left alone.

    Args:
        spec: The OpenAPI specification as a dictionary.

    Returns:
        The transformed specification.
    """
    try:
        headers: dict = spec["components"]["headers"]
    except (KeyError, TypeError):
        return spec

    null_keys = [name for name, value in headers.items() if value is None]
    for name in null_keys:
        del headers[name]

    for name, header in list(headers.items()):
        if not isinstance(header, dict):
            continue
        if "schema" in header or "content" in header:
            continue

        # Determine whether `required` (if present) is a schema list or a
        # header boolean.  A list value means it lists required *properties*
        # (Schema Object semantics).
        required_is_schema_list = isinstance(header.get("required"), list)

        # Only trigger the wrap when at least one unambiguous schema key is
        # present (or `required` is clearly a schema list).
        pure_schema_keys_present = _PURE_SCHEMA_KEYS & header.keys()
        if not pure_schema_keys_present and not required_is_schema_list:
            continue

        schema_obj: dict = {}
        keys_to_remove: list[str] = []

        for key in list(header.keys()):
            if key in _PURE_SCHEMA_KEYS:
                # Pure schema key — move it into schema
                schema_obj[key] = header[key]
                keys_to_remove.append(key)
            elif key == "required" and required_is_schema_list:
                # required-as-list is a schema key — move it
                schema_obj[key] = header[key]
                keys_to_remove.append(key)
            elif key in _DUAL_KEYS:
                # Dual-purpose key — keep at header level AND copy into schema
                schema_obj[key] = header[key]
            # All other keys (_HEADER_ONLY_KEYS, boolean `required`, etc.)
            # remain untouched at the top level.

        for key in keys_to_remove:
            del header[key]

        header["schema"] = schema_obj

    return spec
