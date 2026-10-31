"""Deleting deprecated schema properties must preserve the remaining API contract."""

import json

from bootstrapper.transformers.manager import transform_spec


def transform(tmp_path, spec):
    source = tmp_path / "source.json"
    output = tmp_path / "output.json"
    source.write_text(json.dumps(spec))
    transform_spec(source, output)
    result = json.loads(output.read_text())
    transform_spec(output, output)
    assert json.loads(output.read_text()) == result
    return result


def document(schemas):
    return {
        "openapi": "3.1.0",
        "info": {"title": "Deprecated properties", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": schemas},
    }


def test_removes_deprecated_properties_and_required_entries_without_deleting_payload_data(tmp_path):
    payload = {"deprecated": True, "properties": {"old": {"deprecated": True}}}
    spec = document(
        {
            "Example": {
                "type": "object",
                "required": ["old", "deprecated", "active"],
                "properties": {
                    "old": {"type": "string", "deprecated": True},
                    "deprecated": {"type": "boolean"},
                    "active": {"type": "string", "deprecated": False},
                    "anything": True,
                },
                "default": payload,
                "example": payload,
                "examples": [payload],
                "enum": [payload],
                "x-custom": payload,
            }
        }
    )
    schema = transform(tmp_path, spec)["components"]["schemas"]["Example"]
    assert set(schema["properties"]) == {"deprecated", "active", "anything"}
    assert schema["required"] == ["deprecated", "active"]
    for key in ("default", "example", "x-custom"):
        assert schema[key] == payload
    assert schema["examples"] == [payload]
    assert schema["enum"] == [payload]


def test_nested_array_and_composed_properties_are_pruned(tmp_path):
    deprecated_object = {
        "type": "object",
        "properties": {"old": {"deprecated": True, "type": "string"}},
        "required": ["old"],
    }
    spec = document(
        {
            "Example": {
                "type": "object",
                "properties": {
                    "array": {"type": "array", "items": deprecated_object},
                    "union": {"oneOf": [deprecated_object, {"type": "string"}]},
                    "composed": {"allOf": [deprecated_object]},
                },
                "$defs": {"Nested": deprecated_object},
            }
        }
    )
    schema = transform(tmp_path, spec)["components"]["schemas"]["Example"]
    nodes = [
        schema["properties"]["array"]["items"],
        schema["properties"]["union"]["oneOf"][0],
        schema["properties"]["composed"]["allOf"][0],
        schema["$defs"]["Nested"],
    ]
    for node in nodes:
        assert node["properties"] == {}
        assert "required" not in node


def test_inline_request_response_parameter_and_header_schemas_are_pruned(tmp_path):
    schema = {
        "type": "object",
        "properties": {
            "old": {"type": "string", "deprecated": True},
            "current": {"type": "string"},
        },
    }
    media = {"application/json": {"schema": schema}}
    spec = document({})
    spec["paths"] = {
        "/example": {
            "parameters": [{"name": "filter", "in": "query", "schema": schema}],
            "post": {
                "operationId": "create",
                "requestBody": {"content": media},
                "responses": {
                    "default": {
                        "description": "OK",
                        "content": media,
                        "headers": {"X-Example": {"schema": schema}},
                    }
                },
            },
        }
    }
    spec["components"]["parameters"] = {
        "Reusable": {"name": "filter", "in": "query", "schema": schema}
    }
    spec["components"]["requestBodies"] = {"Reusable": {"content": media}}
    result = transform(tmp_path, spec)
    path = result["paths"]["/example"]
    nodes = [
        path["parameters"][0]["schema"],
        path["post"]["requestBody"]["content"]["application/json"]["schema"],
        path["post"]["responses"]["default"]["content"]["application/json"]["schema"],
        path["post"]["responses"]["default"]["headers"]["X-Example"]["schema"],
        result["components"]["parameters"]["Reusable"]["schema"],
        result["components"]["requestBodies"]["Reusable"]["content"]["application/json"]["schema"],
    ]
    assert all(set(node["properties"]) == {"current"} for node in nodes)


def test_unused_deprecated_models_including_cycles_are_removed_without_dangling_refs(tmp_path):
    spec = document(
        {
            "Current": {
                "type": "object",
                "properties": {"old": {"deprecated": True, "$ref": "#/components/schemas/Old"}},
            },
            "Old": {
                "type": "object",
                "deprecated": True,
                "properties": {"next": {"$ref": "#/components/schemas/OtherOld"}},
            },
            "OtherOld": {
                "type": "object",
                "deprecated": True,
                "properties": {"next": {"$ref": "#/components/schemas/Old"}},
            },
        }
    )
    schemas = transform(tmp_path, spec)["components"]["schemas"]
    assert set(schemas) == {"Current"}
    assert schemas["Current"]["properties"] == {}


def test_deprecated_model_still_used_by_a_surviving_response_is_retained(tmp_path):
    spec = document({"Old": {"type": "object", "deprecated": True}})
    spec["paths"] = {
        "/example": {
            "get": {
                "operationId": "getExample",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Old"}}
                        },
                    }
                },
            }
        }
    }
    assert "Old" in transform(tmp_path, spec)["components"]["schemas"]


def test_callbacks_webhooks_and_named_schemas_are_visited(tmp_path):
    schema = {
        "type": "object",
        "properties": {
            "old": {"type": "string", "deprecated": True},
            "current": {"type": "string"},
        },
    }
    item = {
        "post": {
            "operationId": "receive",
            "requestBody": {"content": {"application/json": {"schema": schema}}},
            "responses": {"200": {"description": "OK"}},
        }
    }
    spec = document({"deprecated": schema})
    spec["webhooks"] = {"incoming": item}
    spec["components"]["callbacks"] = {"Reusable": {"{$request.query.url}": item}}
    spec["paths"] = {
        "/example": {
            "post": {
                "operationId": "create",
                "callbacks": {"onEvent": {"{$request.query.url}": item}},
                "responses": {"200": {"description": "OK"}},
            }
        }
    }
    result = transform(tmp_path, spec)
    nodes = [
        result["components"]["schemas"]["deprecated"],
        result["webhooks"]["incoming"]["post"]["requestBody"]["content"]["application/json"][
            "schema"
        ],
        result["components"]["callbacks"]["Reusable"]["{$request.query.url}"]["post"][
            "requestBody"
        ]["content"]["application/json"]["schema"],
    ]
    assert all(set(node["properties"]) == {"current"} for node in nodes)


def test_escaped_and_percent_encoded_references_keep_deprecated_models_live(tmp_path):
    spec = document(
        {
            "Current": {
                "type": "object",
                "properties": {
                    "a": {"$ref": "#/components/schemas/Old~1Kind"},
                    "b": {"$ref": "#/components/schemas/Old%20Kind"},
                },
            },
            "Old/Kind": {"type": "object", "deprecated": True},
            "Old Kind": {"type": "object", "deprecated": True},
        }
    )
    assert set(transform(tmp_path, spec)["components"]["schemas"]) == {
        "Current",
        "Old/Kind",
        "Old Kind",
    }


def test_discriminator_mapping_by_schema_name_keeps_deprecated_model_live(tmp_path):
    spec = document(
        {
            "Base": {
                "type": "object",
                "properties": {"kind": {"type": "string"}},
                "discriminator": {"propertyName": "kind", "mapping": {"old": "Old"}},
            },
            "Old": {"type": "object", "deprecated": True},
        }
    )
    assert set(transform(tmp_path, spec)["components"]["schemas"]) == {"Base", "Old"}
