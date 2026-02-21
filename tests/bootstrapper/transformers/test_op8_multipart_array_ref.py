"""Tests for op8_multipart_array_ref: fix $ref-to-array in multipart schemas."""

import pytest

from bootstrapper.transformers.op8_multipart_array_ref import fix_multipart_array_refs


def _make_spec(prop_schema: dict, component_schemas: dict | None = None) -> dict:
    """Build a minimal spec with a multipart/form-data POST containing `prop_schema`."""
    spec: dict = {
        "paths": {
            "/upload": {
                "post": {
                    "requestBody": {
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "target_prop": prop_schema,
                                        "name": {"type": "string"},
                                    },
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {"schemas": component_schemas or {}},
    }
    return spec


# ---------------------------------------------------------------------------
# Core bug-fix scenario
# ---------------------------------------------------------------------------


def test_ref_to_array_is_inlined():
    """$ref to type:array should be replaced with inline type:array + items."""
    spec = _make_spec(
        {"$ref": "#/components/schemas/FileList"},
        component_schemas={
            "FileList": {
                "type": "array",
                "items": {"type": "string", "format": "binary"},
            }
        },
    )
    result = fix_multipart_array_refs(spec)
    prop = (
        result["paths"]["/upload"]["post"]["requestBody"]["content"]["multipart/form-data"][
            "schema"
        ]["properties"]["target_prop"]
    )
    assert prop == {"type": "array", "items": {"type": "string", "format": "binary"}}


def test_ref_to_array_with_ref_items():
    """$ref to array whose items is itself a $ref (ElevenLabs pattern)."""
    spec = _make_spec(
        {"$ref": "#/components/schemas/AdditionalFormats"},
        component_schemas={
            "AdditionalFormats": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/ExportOptions"},
            },
            "ExportOptions": {"type": "object", "properties": {"format": {"type": "string"}}},
        },
    )
    result = fix_multipart_array_refs(spec)
    prop = (
        result["paths"]["/upload"]["post"]["requestBody"]["content"]["multipart/form-data"][
            "schema"
        ]["properties"]["target_prop"]
    )
    assert prop == {"type": "array", "items": {"$ref": "#/components/schemas/ExportOptions"}}


def test_description_preserved():
    """Description from the ref'd array schema is preserved in the inlined schema."""
    spec = _make_spec(
        {"$ref": "#/components/schemas/Tags"},
        component_schemas={
            "Tags": {
                "type": "array",
                "description": "A list of tags",
                "items": {"type": "string"},
            }
        },
    )
    result = fix_multipart_array_refs(spec)
    prop = (
        result["paths"]["/upload"]["post"]["requestBody"]["content"]["multipart/form-data"][
            "schema"
        ]["properties"]["target_prop"]
    )
    assert prop["description"] == "A list of tags"
    assert prop["type"] == "array"


# ---------------------------------------------------------------------------
# Non-array refs and other content types are left untouched
# ---------------------------------------------------------------------------


def test_ref_to_object_not_changed():
    """$ref to an object schema should not be modified."""
    spec = _make_spec(
        {"$ref": "#/components/schemas/Config"},
        component_schemas={
            "Config": {"type": "object", "properties": {"key": {"type": "string"}}}
        },
    )
    result = fix_multipart_array_refs(spec)
    prop = (
        result["paths"]["/upload"]["post"]["requestBody"]["content"]["multipart/form-data"][
            "schema"
        ]["properties"]["target_prop"]
    )
    assert prop == {"$ref": "#/components/schemas/Config"}


def test_inline_array_not_changed():
    """A property that is already an inline array schema should be left alone."""
    spec = _make_spec({"type": "array", "items": {"type": "string"}})
    result = fix_multipart_array_refs(spec)
    prop = (
        result["paths"]["/upload"]["post"]["requestBody"]["content"]["multipart/form-data"][
            "schema"
        ]["properties"]["target_prop"]
    )
    assert prop == {"type": "array", "items": {"type": "string"}}


def test_non_multipart_content_not_touched():
    """Properties inside application/json content should not be modified."""
    spec: dict = {
        "paths": {
            "/data": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "items": {"$ref": "#/components/schemas/ItemList"}
                                    },
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "ItemList": {"type": "array", "items": {"type": "string"}},
            }
        },
    }
    result = fix_multipart_array_refs(spec)
    prop = (
        result["paths"]["/data"]["post"]["requestBody"]["content"]["application/json"]["schema"][
            "properties"
        ]["items"]
    )
    # Should still be $ref — we don't touch non-multipart content
    assert prop == {"$ref": "#/components/schemas/ItemList"}


# ---------------------------------------------------------------------------
# components/requestBodies
# ---------------------------------------------------------------------------


def test_components_request_bodies_fixed():
    """$ref-to-array inside components/requestBodies is also fixed."""
    spec: dict = {
        "paths": {},
        "components": {
            "requestBodies": {
                "UploadBody": {
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "files": {"$ref": "#/components/schemas/FileList"}
                                },
                            }
                        }
                    }
                }
            },
            "schemas": {
                "FileList": {
                    "type": "array",
                    "items": {"type": "string", "format": "binary"},
                }
            },
        },
    }
    result = fix_multipart_array_refs(spec)
    prop = (
        result["components"]["requestBodies"]["UploadBody"]["content"]["multipart/form-data"][
            "schema"
        ]["properties"]["files"]
    )
    assert prop == {"type": "array", "items": {"type": "string", "format": "binary"}}


# ---------------------------------------------------------------------------
# Non-multipart property neighbours are untouched
# ---------------------------------------------------------------------------


def test_other_properties_in_same_schema_untouched():
    """Non-problematic properties in the same multipart schema are unchanged."""
    spec = _make_spec(
        {"$ref": "#/components/schemas/FileList"},
        component_schemas={
            "FileList": {"type": "array", "items": {"type": "string", "format": "binary"}}
        },
    )
    result = fix_multipart_array_refs(spec)
    name_prop = (
        result["paths"]["/upload"]["post"]["requestBody"]["content"]["multipart/form-data"][
            "schema"
        ]["properties"]["name"]
    )
    assert name_prop == {"type": "string"}
