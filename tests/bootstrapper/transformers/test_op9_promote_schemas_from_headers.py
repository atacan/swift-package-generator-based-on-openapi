"""Tests for op9_promote_schemas_from_headers: promote misplaced schemas."""

import pytest

from bootstrapper.transformers.op9_promote_schemas_from_headers import (
    promote_misplaced_schemas,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(headers: dict, schemas: dict | None = None, extra_refs: list[str] | None = None) -> dict:
    """Build a minimal spec with the given headers and schemas.

    ``extra_refs`` can inject additional ``$ref`` strings into a path to
    trigger schema-name detection without a real path structure.
    """
    spec: dict = {
        "components": {
            "headers": headers,
            "schemas": schemas if schemas is not None else {},
        }
    }
    if extra_refs:
        spec["x-extra-refs"] = extra_refs
    return spec


# ---------------------------------------------------------------------------
# Core promotion logic
# ---------------------------------------------------------------------------


def test_schema_ref_in_spec_promotes_header_to_schemas():
    """A header referenced via $ref: '#/components/schemas/...' is moved to schemas."""
    spec = _spec(
        headers={
            "StyleId": {
                "description": "A unique ID assigned to a style rule.",
                "example": "bd0a38f3-1831-440b-a8dd-2c702e2325ab",
                "schema": {
                    "type": "string",
                    "description": "A unique ID assigned to a style rule.",
                    "example": "bd0a38f3-1831-440b-a8dd-2c702e2325ab",
                },
            }
        },
        extra_refs=["#/components/schemas/StyleId"],
    )
    result = promote_misplaced_schemas(spec)

    assert "StyleId" not in result["components"]["headers"]
    assert result["components"]["schemas"]["StyleId"] == {
        "type": "string",
        "description": "A unique ID assigned to a style rule.",
        "example": "bd0a38f3-1831-440b-a8dd-2c702e2325ab",
    }


def test_uses_nested_schema_key_when_present():
    """The nested ``schema`` sub-object (added by op7) is used, not the raw header."""
    raw_header = {
        "description": "Desc",
        "schema": {"type": "string", "description": "Desc"},
    }
    spec = _spec(
        headers={"MySchema": raw_header},
        extra_refs=["#/components/schemas/MySchema"],
    )
    result = promote_misplaced_schemas(spec)

    # Should be the inner schema object, not the wrapper
    assert result["components"]["schemas"]["MySchema"] == {"type": "string", "description": "Desc"}


def test_falls_back_to_raw_header_when_no_schema_key():
    """When the header has no 'schema' sub-key, the raw header dict is used."""
    raw_header = {"type": "string", "description": "Bare header"}
    spec = _spec(
        headers={"BareHeader": raw_header},
        extra_refs=["#/components/schemas/BareHeader"],
    )
    result = promote_misplaced_schemas(spec)

    assert result["components"]["schemas"]["BareHeader"] == raw_header


def test_multiple_misplaced_headers_all_promoted():
    """All headers that are schema-referenced but absent from schemas are promoted."""
    spec = _spec(
        headers={
            "ConfiguredRules": {
                "schema": {"type": "object", "description": "Configured rules."}
            },
            "StyleRuleLanguage": {
                "schema": {"type": "string", "enum": ["en", "de"]}
            },
            "X-Trace-ID": {"schema": {"type": "string"}},  # real header, not referenced as schema
        },
        extra_refs=[
            "#/components/schemas/ConfiguredRules",
            "#/components/schemas/StyleRuleLanguage",
        ],
    )
    result = promote_misplaced_schemas(spec)

    assert "ConfiguredRules" not in result["components"]["headers"]
    assert "StyleRuleLanguage" not in result["components"]["headers"]
    assert "X-Trace-ID" in result["components"]["headers"]  # untouched
    assert result["components"]["schemas"]["ConfiguredRules"] == {
        "type": "object",
        "description": "Configured rules.",
    }
    assert result["components"]["schemas"]["StyleRuleLanguage"] == {
        "type": "string",
        "enum": ["en", "de"],
    }


# ---------------------------------------------------------------------------
# No-op cases
# ---------------------------------------------------------------------------


def test_header_not_referenced_as_schema_is_untouched():
    """A header that is only used as a header ref is not moved."""
    spec = _spec(
        headers={"X-Trace-ID": {"schema": {"type": "string"}}},
        # No $ref to #/components/schemas/X-Trace-ID
    )
    result = promote_misplaced_schemas(spec)

    assert "X-Trace-ID" in result["components"]["headers"]
    assert "X-Trace-ID" not in result["components"]["schemas"]


def test_schema_already_in_schemas_is_not_overwritten():
    """If the name already exists in components.schemas, it is left alone."""
    existing = {"type": "integer"}
    spec = _spec(
        headers={"StyleId": {"schema": {"type": "string"}}},
        schemas={"StyleId": existing},
        extra_refs=["#/components/schemas/StyleId"],
    )
    result = promote_misplaced_schemas(spec)

    # The existing schema must not be replaced
    assert result["components"]["schemas"]["StyleId"] == existing
    # The header stays because we didn't touch it (name was already in schemas)
    assert "StyleId" in result["components"]["headers"]


def test_no_components_headers_returns_spec_unchanged():
    """Spec without components.headers is returned as-is."""
    spec: dict = {"openapi": "3.1.0", "components": {"schemas": {}}}
    result = promote_misplaced_schemas(spec)
    assert result == spec


def test_no_components_returns_spec_unchanged():
    """Spec without components at all is returned as-is."""
    spec: dict = {"openapi": "3.1.0"}
    result = promote_misplaced_schemas(spec)
    assert result == spec


def test_schemas_key_created_if_missing():
    """components.schemas is created when absent and a promotion occurs."""
    spec: dict = {
        "components": {
            "headers": {
                "MySchema": {"schema": {"type": "string"}},
            }
            # no "schemas" key
        },
        "x-extra-refs": ["#/components/schemas/MySchema"],
    }
    result = promote_misplaced_schemas(spec)

    assert "schemas" in result["components"]
    assert result["components"]["schemas"]["MySchema"] == {"type": "string"}


def test_ref_detected_deep_in_spec():
    """$ref strings inside nested path/response objects are detected."""
    spec: dict = {
        "paths": {
            "/style": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/StyleId"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "headers": {
                "StyleId": {
                    "schema": {"type": "string", "description": "Style ID"}
                }
            },
            "schemas": {},
        },
    }
    result = promote_misplaced_schemas(spec)

    assert "StyleId" not in result["components"]["headers"]
    assert result["components"]["schemas"]["StyleId"] == {
        "type": "string",
        "description": "Style ID",
    }
