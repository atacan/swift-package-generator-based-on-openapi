"""Prove mapping inference against the actual OpenAI overlay fixes and unsafe unions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from bootstrapper.main import app
from bootstrapper.transformers.manager import transform_spec
from bootstrapper.transformers.op2_const_enum import convert_const_to_enum
from bootstrapper.transformers.op14_discriminator_mappings import infer_discriminator_mappings

FIXTURE = yaml.safe_load(
    (Path(__file__).parent / "fixtures" / "openai_discriminator_mappings.yaml").read_text()
)


def at_path(spec, path):
    for part in path:
        spec = spec[part]
    return spec


@pytest.mark.parametrize(
    "example", FIXTURE["expected"], ids=lambda example: ".".join(example["path"][2:])
)
def test_reproduces_exact_openai_overlay_mapping(example):
    spec = deepcopy(FIXTURE["spec"])
    original = deepcopy(at_path(spec, example["path"]))
    assert "mapping" not in original["discriminator"]

    infer_discriminator_mappings(spec)

    result = at_path(spec, example["path"])
    assert result["discriminator"]["mapping"] == example["mapping"]
    original["discriminator"]["mapping"] = example["mapping"]
    assert result == original  # Mapping inference must not change the union shape.


def test_full_pipeline_reproduces_all_12_mappings_and_174_entries(tmp_path):
    assert FIXTURE["provenance"]["mapping_action_count"] == len(FIXTURE["expected"]) == 12
    assert sum(len(example["mapping"]) for example in FIXTURE["expected"]) == 174
    source = tmp_path / "original.json"
    output = tmp_path / "openapi.json"
    source.write_text(json.dumps(FIXTURE["spec"]))

    transform_spec(source, output)

    result = json.loads(output.read_text())
    for example in FIXTURE["expected"]:
        assert at_path(result, example["path"])["discriminator"]["mapping"] == example["mapping"]
    schemas = result["components"]["schemas"]
    assert "oneOf" in schemas["RealtimeServerEvent"]  # op13 runs before mapping inference.
    for name in FIXTURE["unsafe_roots"]:
        assert "mapping" not in schemas[name].get("discriminator", {})
    transform_spec(output, output)
    assert json.loads(output.read_text()) == result


def test_overlay_runs_after_inference_and_can_override_it(tmp_path, monkeypatch):
    source = tmp_path / "original.json"
    output = tmp_path / "openapi.json"
    overlay = tmp_path / "overlay.yaml"
    source.write_text(json.dumps(FIXTURE["spec"]))
    overlay.write_text("overlay: 1.0.0\nactions: []\n")
    example = FIXTURE["expected"][0]

    def apply_overlay(output_path, overlay_path):
        assert overlay_path == overlay
        transformed = json.loads(output_path.read_text())
        discriminator = at_path(transformed, example["path"])["discriminator"]
        assert discriminator["mapping"] == example["mapping"]
        discriminator["mapping"] = {"manual": "#/components/schemas/Manual"}
        output_path.write_text(json.dumps(transformed))
        return {"applied": True, "skipped": False, "reason": "Applied test override"}

    monkeypatch.setattr("bootstrapper.main.apply_overlay_file", apply_overlay)
    result = CliRunner().invoke(
        app, ["transform", str(source), str(output), "--overlay", str(overlay)]
    )
    assert result.exit_code == 0, result.output
    assert at_path(json.loads(output.read_text()), example["path"])["discriminator"]["mapping"] == {
        "manual": "#/components/schemas/Manual"
    }


@pytest.mark.parametrize("name", FIXTURE["unsafe_roots"])
def test_exact_openai_unsafe_examples_remain_unchanged(name):
    spec = deepcopy(FIXTURE["spec"])
    expected = deepcopy(spec["components"]["schemas"][name])
    infer_discriminator_mappings(spec)
    assert spec["components"]["schemas"][name] == expected


@pytest.fixture
def spec():
    return {
        "components": {
            "schemas": {
                "A": {
                    "type": "object",
                    "required": ["kind"],
                    "properties": {"kind": {"type": "string", "enum": ["a", "a2"]}},
                },
                "B": {
                    "type": "object",
                    "required": ["kind"],
                    "properties": {"kind": {"type": "string", "const": "b"}},
                },
                "Union": {
                    "oneOf": [
                        {"$ref": "#/components/schemas/A"},
                        {"$ref": "#/components/schemas/B"},
                    ],
                    "discriminator": {"propertyName": "kind"},
                },
            }
        }
    }


def test_multiple_values_const_normalization_and_idempotence(spec):
    expected = deepcopy(spec)
    expected["components"]["schemas"]["Union"]["discriminator"]["mapping"] = {
        "a": "#/components/schemas/A",
        "a2": "#/components/schemas/A",
        "b": "#/components/schemas/B",
    }
    assert infer_discriminator_mappings(spec) == expected
    assert infer_discriminator_mappings(spec) == expected
    assert infer_discriminator_mappings(convert_const_to_enum(spec)) == convert_const_to_enum(
        expected
    )


@pytest.mark.parametrize("union", ["anyOf", "oneOf"])
def test_preserves_existing_mapping_and_explicit_aliases(spec, union):
    schema = spec["components"]["schemas"]["Union"]
    schema[union] = schema.pop("oneOf")
    schema["discriminator"]["mapping"] = {
        "a": "#/components/schemas/A",
        "legacy_a": "#/components/schemas/A",
    }
    infer_discriminator_mappings(spec)
    assert schema["discriminator"]["mapping"] == {
        "a": "#/components/schemas/A",
        "legacy_a": "#/components/schemas/A",
        "a2": "#/components/schemas/A",
        "b": "#/components/schemas/B",
    }


def test_allof_combines_required_properties_types_and_intersects_values(spec):
    schemas = spec["components"]["schemas"]
    schemas["A"] = {
        "allOf": [
            {"$ref": "#/components/schemas/ObjectBase"},
            {"required": ["kind"]},
            {"properties": {"kind": {"$ref": "#/components/schemas/Tag"}}},
            {"properties": {"kind": {"allOf": [{"enum": ["a", "b"]}, {"const": "a"}]}}},
        ]
    }
    schemas["ObjectBase"] = {"type": "object"}
    schemas["Tag"] = {"type": "string", "enum": ["a", "a2", "b"]}
    infer_discriminator_mappings(spec)
    assert schemas["Union"]["discriminator"]["mapping"] == {
        "a": "#/components/schemas/A",
        "b": "#/components/schemas/B",
    }


def test_recursive_local_refs_and_json_pointer_escaping(spec):
    schemas = spec["components"]["schemas"]
    schemas["A/~"] = schemas.pop("A")
    schemas["Alias"] = {"$ref": "#/components/schemas/A~1~0"}
    schemas["Union"]["oneOf"][0] = {"$ref": "#/components/schemas/Alias"}
    schemas["B"]["properties"]["kind"] = {"$ref": "#/components/schemas/A~1~0/properties/kind"}
    # The property ref and its sibling const both apply; avoid the original tag values.
    schemas["B"]["properties"]["kind"]["const"] = "a"
    expected = deepcopy(spec)
    assert infer_discriminator_mappings(spec) == expected  # a now overlaps across branches.
    schemas["B"]["properties"]["kind"] = {"const": "b"}
    infer_discriminator_mappings(spec)
    assert schemas["Union"]["discriminator"]["mapping"] == {
        "a": "#/components/schemas/Alias",
        "a2": "#/components/schemas/Alias",
        "b": "#/components/schemas/B",
    }


@pytest.mark.parametrize(
    ("index", "valid"),
    [
        ("0", True),
        ("1", True),
        ("10", True),
        ("00", False),
        ("01", False),
        ("٠", False),
        ("１", False),
        ("-1", False),
        ("-", False),
        ("11", False),
        pytest.param("9" * 5000, False, id="oversized-index"),
    ],
)
def test_json_pointer_array_indices_follow_rfc_6901(spec, index, valid):
    spec["x-tag-definitions"] = [{"enum": ["a", "a2"]} for _ in range(11)]
    schemas = spec["components"]["schemas"]
    schemas["A"]["properties"]["kind"] = {"$ref": f"#/x-tag-definitions/{index}"}
    expected = deepcopy(spec)
    if valid:
        expected["components"]["schemas"]["Union"]["discriminator"]["mapping"] = {
            "a": "#/components/schemas/A",
            "a2": "#/components/schemas/A",
            "b": "#/components/schemas/B",
        }
    assert infer_discriminator_mappings(spec) == expected


@pytest.mark.parametrize("location", ["branch", "object", "property"])
def test_ref_siblings_constrain_tags_with_and_semantics(spec, location):
    schemas = spec["components"]["schemas"]
    schema = schemas["Union"]
    constraint = {"properties": {"kind": {"const": "a2"}}}
    if location == "branch":
        schema["oneOf"][0].update(constraint)
    elif location == "object":
        schemas["Base"] = schemas["A"]
        schemas["A"] = {"$ref": "#/components/schemas/Base", **constraint}
    else:
        schemas["Tag"] = schemas["A"]["properties"]["kind"]
        schemas["A"]["properties"]["kind"] = {
            "$ref": "#/components/schemas/Tag",
            "const": "a2",
        }
    infer_discriminator_mappings(spec)
    assert schema["discriminator"]["mapping"] == {
        "a2": "#/components/schemas/A",
        "b": "#/components/schemas/B",
    }


@pytest.mark.parametrize(
    "change",
    [
        "overlap",
        "optional_tag",
        "missing_tag",
        "unbounded_tag",
        "empty_enum",
        "non_string_enum",
        "mixed_enum",
        "non_string_const",
        "conflicting_const_enum",
        "non_object_branch",
        "unspecified_object_type",
        "nullable_object_type",
        "conflicting_allof_tag",
        "conflicting_allof_tag_type",
        "conflicting_allof_type",
        "unresolved_branch",
        "external_branch",
        "inline_branch",
        "boolean_branch",
        "cyclic_object_ref",
        "cyclic_property_ref",
        "external_property_ref",
        "unresolved_allof_ref",
        "nested_union",
        "property_union",
        "conflicting_branch_ref_sibling",
        "conflicting_property_ref_sibling",
        "missing_discriminator",
        "invalid_discriminator",
        "invalid_property_name",
        "conflicting_existing_mapping",
        "invalid_existing_mapping",
        "both_union_keywords",
    ],
)
def test_leaves_unproven_or_conflicting_unions_unchanged(spec, change):
    schemas = spec["components"]["schemas"]
    union = schemas["Union"]
    tag = schemas["A"]["properties"]["kind"]
    if change == "overlap":
        schemas["B"]["properties"]["kind"] = {"const": "a2"}
    elif change == "optional_tag":
        schemas["A"].pop("required")
    elif change == "missing_tag":
        schemas["A"]["properties"].pop("kind")
    elif change == "unbounded_tag":
        tag.pop("enum")
    elif change == "empty_enum":
        tag["enum"] = []
    elif change == "non_string_enum":
        tag["enum"] = [42]
    elif change == "mixed_enum":
        tag.pop("type")
        tag["enum"] = ["a", 42]
    elif change == "non_string_const":
        schemas["B"]["properties"]["kind"]["const"] = 42
    elif change == "conflicting_const_enum":
        tag["const"] = "b"
    elif change == "non_object_branch":
        schemas["A"]["type"] = "string"
    elif change == "unspecified_object_type":
        schemas["A"].pop("type")
    elif change == "nullable_object_type":
        schemas["A"]["type"] = ["object", "null"]
    elif change == "conflicting_allof_tag":
        schemas["A"]["allOf"] = [{"properties": {"kind": {"const": "b"}}}]
    elif change == "conflicting_allof_tag_type":
        schemas["A"]["allOf"] = [{"properties": {"kind": {"type": "integer"}}}]
    elif change == "conflicting_allof_type":
        schemas["A"]["allOf"] = [{"type": "string"}]
    elif change in {"unresolved_branch", "external_branch"}:
        ref = "#/components/schemas/Missing" if change == "unresolved_branch" else "other.yaml#/A"
        union["oneOf"][0] = {"$ref": ref}
    elif change == "inline_branch":
        union["oneOf"][0] = deepcopy(schemas["A"])
    elif change == "boolean_branch":
        schemas["A"] = True
    elif change == "cyclic_object_ref":
        schemas["A"]["allOf"] = [{"$ref": "#/components/schemas/A"}]
    elif change == "cyclic_property_ref":
        tag["$ref"] = "#/components/schemas/A/properties/kind"
    elif change == "external_property_ref":
        tag["$ref"] = "other.yaml#/Tag"
    elif change == "unresolved_allof_ref":
        schemas["A"]["allOf"] = [{"$ref": "#/components/schemas/Missing"}]
    elif change == "nested_union":
        schemas["A"]["oneOf"] = [{"const": {}}, {"const": {"kind": "a"}}]
    elif change == "property_union":
        tag["anyOf"] = [{"const": "a"}, {"const": "a2"}]
    elif change == "conflicting_branch_ref_sibling":
        union["oneOf"][0]["properties"] = {"kind": {"const": "b"}}
    elif change == "conflicting_property_ref_sibling":
        schemas["Tag"] = deepcopy(tag)
        tag.clear()
        tag.update({"$ref": "#/components/schemas/Tag", "const": "b"})
    elif change == "missing_discriminator":
        union.pop("discriminator")
    elif change == "invalid_discriminator":
        union["discriminator"] = "kind"
    elif change == "invalid_property_name":
        union["discriminator"]["propertyName"] = 42
    elif change == "conflicting_existing_mapping":
        union["discriminator"]["mapping"] = {"a2": "#/components/schemas/B"}
    elif change == "invalid_existing_mapping":
        union["discriminator"]["mapping"] = ["a", "A"]
    elif change == "both_union_keywords":
        union["anyOf"] = deepcopy(union["oneOf"])
    expected = deepcopy(spec)
    assert infer_discriminator_mappings(spec) == expected
