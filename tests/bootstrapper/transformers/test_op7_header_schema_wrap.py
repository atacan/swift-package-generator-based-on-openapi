"""Tests for op7_header_schema_wrap: fix Header Objects missing `schema` wrapper."""

import pytest

from bootstrapper.transformers.op7_header_schema_wrap import fix_header_schemas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec_with_headers(headers: dict) -> dict:
    return {"components": {"headers": headers}}


# ---------------------------------------------------------------------------
# Rule 1: Wrap bare schema keys into `schema`
# ---------------------------------------------------------------------------


def test_bare_type_and_enum_are_wrapped():
    """Header with bare type/enum gets a schema sub-object."""
    spec = _spec_with_headers(
        {
            "StyleRuleLanguage": {
                "description": "The language for the style rule.",
                "type": "string",
                "enum": ["en", "de", "fr"],
            }
        }
    )
    result = fix_header_schemas(spec)
    header = result["components"]["headers"]["StyleRuleLanguage"]

    assert "schema" in header
    assert header["schema"]["type"] == "string"
    assert header["schema"]["enum"] == ["en", "de", "fr"]
    # description kept at top level
    assert header["description"] == "The language for the style rule."
    # description also copied into schema
    assert header["schema"]["description"] == "The language for the style rule."
    # type/enum moved out of top level
    assert "type" not in header
    assert "enum" not in header


def test_bare_properties_object_is_wrapped():
    """Header with bare type/properties gets a schema sub-object."""
    spec = _spec_with_headers(
        {
            "ConfiguredRules": {
                "description": "Configured rules.",
                "type": "object",
                "properties": {"rule": {"type": "string"}},
            }
        }
    )
    result = fix_header_schemas(spec)
    header = result["components"]["headers"]["ConfiguredRules"]

    assert header["schema"]["type"] == "object"
    assert "properties" in header["schema"]
    assert "type" not in header
    assert "properties" not in header


def test_example_kept_at_top_and_in_schema():
    """example is a dual-purpose key: stays at header level and is copied into schema."""
    spec = _spec_with_headers(
        {
            "StyleId": {
                "type": "string",
                "description": "A style identifier.",
                "example": "style-001",
            }
        }
    )
    result = fix_header_schemas(spec)
    header = result["components"]["headers"]["StyleId"]

    assert header["example"] == "style-001"
    assert header["schema"]["example"] == "style-001"
    # type is a pure schema key — moved
    assert "type" not in header
    assert header["schema"]["type"] == "string"


def test_required_and_properties_wrapped():
    """Headers with type/required/properties have those moved into schema."""
    spec = _spec_with_headers(
        {
            "CreateGlossaryParameters": {
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string"}},
            }
        }
    )
    result = fix_header_schemas(spec)
    header = result["components"]["headers"]["CreateGlossaryParameters"]

    assert header["schema"]["type"] == "object"
    assert header["schema"]["required"] == ["name"]
    assert "properties" in header["schema"]
    assert "type" not in header
    assert "required" not in header


# ---------------------------------------------------------------------------
# Rule 2: Remove null headers
# ---------------------------------------------------------------------------


def test_null_header_is_removed():
    """A header whose value is null is removed from the map."""
    spec = _spec_with_headers(
        {
            "DocumentTranslationError": None,
            "ValidHeader": {"schema": {"type": "string"}},
        }
    )
    result = fix_header_schemas(spec)
    assert "DocumentTranslationError" not in result["components"]["headers"]
    assert "ValidHeader" in result["components"]["headers"]


def test_all_null_headers_removed():
    """All null headers are removed when the map contains only nulls."""
    spec = _spec_with_headers({"A": None, "B": None})
    result = fix_header_schemas(spec)
    assert result["components"]["headers"] == {}


# ---------------------------------------------------------------------------
# Already-valid headers are left untouched
# ---------------------------------------------------------------------------


def test_header_with_schema_key_unchanged():
    """A header that already has a `schema` key is not modified."""
    original = {"description": "x", "schema": {"type": "string"}}
    spec = _spec_with_headers({"MyHeader": dict(original)})
    result = fix_header_schemas(spec)
    assert result["components"]["headers"]["MyHeader"] == original


def test_header_with_content_key_unchanged():
    """A header that already has a `content` key is not modified."""
    original = {"content": {"text/plain": {"schema": {"type": "string"}}}}
    spec = _spec_with_headers({"MyHeader": dict(original)})
    result = fix_header_schemas(spec)
    assert result["components"]["headers"]["MyHeader"] == original


def test_header_meta_only_keys_unchanged():
    """A header with only valid header-meta keys (no schema keys) is unchanged."""
    original = {"deprecated": True, "required": False}
    spec = _spec_with_headers({"MyHeader": dict(original)})
    result = fix_header_schemas(spec)
    assert result["components"]["headers"]["MyHeader"] == original


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_no_components_headers_key():
    """Spec without components.headers is returned unchanged."""
    spec: dict = {"openapi": "3.1.0", "info": {"title": "T", "version": "1"}}
    result = fix_header_schemas(spec)
    assert result == spec


def test_no_components_key():
    """Spec without components is returned unchanged."""
    spec: dict = {"openapi": "3.1.0"}
    result = fix_header_schemas(spec)
    assert result == spec


def test_multiple_headers_processed_independently():
    """Multiple headers in the same spec are each processed."""
    spec = _spec_with_headers(
        {
            "H1": {"type": "string", "enum": ["a", "b"]},
            "H2": None,
            "H3": {"schema": {"type": "integer"}},
        }
    )
    result = fix_header_schemas(spec)
    headers = result["components"]["headers"]

    assert "schema" in headers["H1"]
    assert headers["H1"]["schema"]["type"] == "string"
    assert "H2" not in headers
    assert headers["H3"] == {"schema": {"type": "integer"}}
