"""Tests for op11_multipart_required: require multipart request bodies."""

from bootstrapper.transformers.op11_multipart_required import require_multipart_request_bodies


def test_multipart_request_body_without_required_is_marked_required():
    spec = {
        "paths": {
            "/transcriptions:transcribe": {
                "post": {
                    "requestBody": {
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "audio": {"type": "string", "format": "binary"},
                                        "definition": {"type": "string"},
                                    },
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    result = require_multipart_request_bodies(spec)

    assert result["paths"]["/transcriptions:transcribe"]["post"]["requestBody"]["required"] is True


def test_multipart_request_body_with_false_required_is_marked_required():
    spec = {
        "paths": {
            "/upload": {
                "post": {
                    "requestBody": {
                        "required": False,
                        "content": {"multipart/form-data": {"schema": {"type": "object"}}},
                    }
                }
            }
        }
    }

    result = require_multipart_request_bodies(spec)

    assert result["paths"]["/upload"]["post"]["requestBody"]["required"] is True


def test_non_multipart_request_body_is_untouched():
    spec = {
        "paths": {
            "/data": {
                "post": {
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}}
                }
            }
        }
    }

    result = require_multipart_request_bodies(spec)

    assert "required" not in result["paths"]["/data"]["post"]["requestBody"]


def test_referenced_component_request_body_is_marked_required():
    spec = {
        "paths": {
            "/upload": {"post": {"requestBody": {"$ref": "#/components/requestBodies/UploadBody"}}}
        },
        "components": {
            "requestBodies": {
                "UploadBody": {"content": {"multipart/form-data": {"schema": {"type": "object"}}}}
            }
        },
    }

    result = require_multipart_request_bodies(spec)

    assert result["paths"]["/upload"]["post"]["requestBody"] == {
        "$ref": "#/components/requestBodies/UploadBody"
    }
    assert result["components"]["requestBodies"]["UploadBody"]["required"] is True


def test_components_request_bodies_are_marked_required_without_path_reference():
    spec = {
        "paths": {},
        "components": {
            "requestBodies": {
                "UploadBody": {
                    "required": False,
                    "content": {"multipart/form-data": {"schema": {"type": "object"}}},
                },
                "JsonBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
            }
        },
    }

    result = require_multipart_request_bodies(spec)

    assert result["components"]["requestBodies"]["UploadBody"]["required"] is True
    assert "required" not in result["components"]["requestBodies"]["JsonBody"]


def test_external_request_body_ref_is_ignored():
    spec = {
        "paths": {
            "/upload": {
                "post": {
                    "requestBody": {"$ref": "common.yaml#/components/requestBodies/UploadBody"}
                }
            }
        }
    }

    result = require_multipart_request_bodies(spec)

    assert result == spec
