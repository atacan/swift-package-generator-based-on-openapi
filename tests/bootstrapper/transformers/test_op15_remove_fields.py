"""Tests for removing selected fields from OpenAPI specifications."""

import json

from bootstrapper.transformers import op15_remove_fields
from bootstrapper.transformers.manager import transform_spec
from bootstrapper.transformers.op15_remove_fields import remove_fields


def test_removes_selected_fields_recursively_and_preserves_other_fields():
    spec = {
        "x-codeSamples": [{"lang": "Shell", "source": "curl /users"}],
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "x-codeSamples": [{"lang": "Swift", "source": "listUsers()"}],
                    "x-custom": {"enabled": True},
                    "parameters": [{"name": "limit", "x-codeSamples": []}],
                }
            }
        },
    }

    result = remove_fields(spec)

    assert result == {
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "x-custom": {"enabled": True},
                    "parameters": [{"name": "limit"}],
                }
            }
        }
    }
    assert remove_fields(result) == result


def test_preserves_spec_without_selected_fields():
    spec = {"openapi": "3.1.0", "paths": {}, "x-custom": [None, "example", 1]}

    assert remove_fields(spec) == spec


def test_supports_adding_other_fields(monkeypatch):
    monkeypatch.setattr(
        op15_remove_fields,
        "FIELDS_TO_REMOVE",
        op15_remove_fields.FIELDS_TO_REMOVE | {"x-extra"},
    )
    spec = {
        "x-codeSamples": [],
        "x-extra": "root metadata",
        "nested": [{"x-extra": "nested metadata", "description": "Keep this"}],
    }

    assert remove_fields(spec) == {"nested": [{"description": "Keep this"}]}


def test_pipeline_removes_code_samples(tmp_path):
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Code samples", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "x-codeSamples": [{"lang": "Shell", "source": "curl /users"}],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
    original = tmp_path / "original.json"
    transformed = tmp_path / "transformed.json"
    original.write_text(json.dumps(spec))

    transform_spec(original, transformed)

    expected = json.loads(json.dumps(spec))
    del expected["paths"]["/users"]["get"]["x-codeSamples"]
    assert json.loads(transformed.read_text()) == expected
