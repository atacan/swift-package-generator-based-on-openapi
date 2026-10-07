"""Regression tests for interactions between transformations."""

import json

import pytest

from bootstrapper.transformers.manager import transform_spec


@pytest.mark.parametrize("union", ["anyOf", "oneOf"])
def test_nullable_required_fields_are_detected_before_null_branches_are_removed(tmp_path, union):
    """Nested completions and error payloads must keep their nullable fields optional."""
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Nullable responses", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Completion": {
                    "type": "object",
                    "required": ["choices"],
                    "properties": {
                        "choices": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["index", "message", "logprobs"],
                                "properties": {
                                    "index": {"type": "integer"},
                                    "message": {"$ref": "#/components/schemas/Message"},
                                    "logprobs": {
                                        union: [
                                            {
                                                "type": "object",
                                                "required": ["content", "refusal"],
                                                "properties": {
                                                    name: {
                                                        union: [
                                                            {
                                                                "type": "array",
                                                                "items": {"type": "string"},
                                                            },
                                                            {"type": "null"},
                                                        ]
                                                    }
                                                    for name in ["content", "refusal"]
                                                },
                                            },
                                            {"type": "null"},
                                        ]
                                    },
                                },
                            },
                        },
                    },
                },
                "Message": {
                    "type": "object",
                    "required": ["role", "content"],
                    "properties": {
                        "role": {"type": "string", "enum": ["assistant"]},
                        "content": {union: [{"type": "string"}, {"type": "null"}]},
                    },
                },
                "Error": {
                    "type": "object",
                    "required": ["type", "message", "param", "code"],
                    "properties": {
                        "type": {"type": "string"},
                        "message": {"type": "string"},
                        "param": {union: [{"type": "string"}, {"type": "null"}]},
                        "code": {union: [{"type": "string"}, {"type": "null"}]},
                    },
                },
            },
        },
    }
    original = tmp_path / "original.json"
    transformed = tmp_path / "transformed.json"
    original.write_text(json.dumps(spec))

    transform_spec(original, transformed)

    schemas = json.loads(transformed.read_text())["components"]["schemas"]
    choice = schemas["Completion"]["properties"]["choices"]["items"]
    assert choice["required"] == ["index", "message"]
    logprobs = choice["properties"]["logprobs"]
    assert not logprobs.get("required")
    assert logprobs["properties"]["refusal"]["type"] == "array"
    assert schemas["Message"]["required"] == ["role"]
    assert schemas["Error"]["required"] == ["type", "message"]
    assert schemas["Error"]["properties"]["param"]["type"] == "string"

    # Re-running the pipeline must preserve the same contract.
    transform_spec(transformed, transformed)
    assert json.loads(transformed.read_text())["components"]["schemas"] == schemas
