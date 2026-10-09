"""Regression tests for disjoint tagged anyOf schemas in the Swift pipeline."""

import json
from copy import deepcopy

import pytest

from bootstrapper.transformers.manager import transform_spec
from bootstrapper.transformers.op13_discriminated_anyof import normalize_discriminated_anyof


def test_pipeline_normalizes_disjoint_tagged_anyof(tmp_path):
    branches = {
        name: {
            "type": "object",
            "properties": {"type": {"type": "string", "const": tag}},
            "required": ["type"],
        }
        for name, tag in [("Created", "response.created"), ("Completed", "response.completed")]
    }
    alternatives = [{"$ref": f"#/components/schemas/{name}"} for name in branches]
    discriminator = {
        "propertyName": "type",
        "mapping": {"response.created": "#/components/schemas/Created"},
    }
    spec = {
        "components": {
            "schemas": {
                **branches,
                "Event": {
                    "anyOf": alternatives,
                    "discriminator": discriminator,
                },
            }
        }
    }
    source = tmp_path / "original.json"
    output = tmp_path / "openapi.json"
    source.write_text(json.dumps(spec))

    transform_spec(source, output)

    event = json.loads(output.read_text())["components"]["schemas"]["Event"]
    assert "anyOf" not in event
    assert event["oneOf"] == alternatives
    assert event["discriminator"] == {
        "propertyName": "type",
        "mapping": {
            **discriminator["mapping"],
            "response.completed": "#/components/schemas/Completed",
        },
    }


@pytest.fixture
def spec():
    return {
        "components": {
            "schemas": {
                "A": {
                    "type": "object",
                    "properties": {"kind": {"enum": ["a", "a2"]}},
                    "required": ["kind"],
                },
                "B": {
                    "type": "object",
                    "properties": {"kind": {"enum": ["b"]}},
                    "required": ["kind"],
                },
                "Union": {
                    "description": "A tagged union",
                    "anyOf": [
                        {"$ref": "#/components/schemas/A"},
                        {"$ref": "#/components/schemas/B"},
                    ],
                    "discriminator": {"propertyName": "kind"},
                },
            }
        }
    }


def test_preserves_branches_metadata_and_is_idempotent(spec):
    expected = deepcopy(spec)
    union = expected["components"]["schemas"]["Union"]
    union["oneOf"] = union.pop("anyOf")
    assert normalize_discriminated_anyof(spec) == expected
    assert normalize_discriminated_anyof(spec) == expected


@pytest.mark.parametrize(
    "change",
    [
        "overlap",
        "optional_tag",
        "missing_enum",
        "non_string_enum",
        "non_object_branch",
        "unspecified_branch_type",
        "boolean_schema",
        "unresolved_ref",
        "external_ref",
        "inline_branch",
        "no_discriminator",
        "existing_oneof",
    ],
)
def test_leaves_unproven_unions_unchanged(spec, change):
    schemas = spec["components"]["schemas"]
    union = schemas["Union"]
    if change == "overlap":
        schemas["B"]["properties"]["kind"]["enum"] = ["b", "a2"]
    elif change == "optional_tag":
        del schemas["B"]["required"]
    elif change == "missing_enum":
        schemas["B"]["properties"]["kind"] = {"type": "string"}
    elif change == "non_string_enum":
        schemas["B"]["properties"]["kind"]["enum"] = [42]
    elif change == "non_object_branch":
        schemas["B"]["type"] = "string"
    elif change == "unspecified_branch_type":
        del schemas["B"]["type"]
    elif change == "boolean_schema":
        schemas["B"] = True
    elif change == "unresolved_ref":
        union["anyOf"][1] = {"$ref": "#/components/schemas/Missing"}
    elif change == "external_ref":
        union["anyOf"][1] = {"$ref": "other.yaml#/components/schemas/B"}
    elif change == "inline_branch":
        union["anyOf"][1] = deepcopy(schemas["B"])
    elif change == "no_discriminator":
        del union["discriminator"]
    elif change == "existing_oneof":
        union["oneOf"] = [{"type": "object"}]
    expected = deepcopy(spec)
    assert normalize_discriminated_anyof(spec) == expected
