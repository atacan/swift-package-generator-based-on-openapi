"""Tests for Operation 4: Convert format byte to contentEncoding base64."""

from bootstrapper.transformers.op5_format_fix import fix_byte_format


class TestOp4FormatByteFix:
    """Tests for Operation 4: Convert format byte to contentEncoding base64."""

    def test_format_byte_converted_in_31_spec(self):
        """Test that format: byte is converted to contentEncoding: base64 for OpenAPI 3.1+."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "File": {
                        "type": "object",
                        "properties": {"data": {"type": "string", "format": "byte"}},
                    }
                }
            },
        }

        result = fix_byte_format(schema)

        data_prop = result["components"]["schemas"]["File"]["properties"]["data"]
        assert "format" not in data_prop
        assert data_prop["contentEncoding"] == "base64"
        assert data_prop["type"] == "string"

    def test_format_byte_unchanged_in_30_spec(self):
        """Test that format: byte is left unchanged for OpenAPI 3.0.x."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "File": {
                        "type": "object",
                        "properties": {"data": {"type": "string", "format": "byte"}},
                    }
                }
            },
        }

        result = fix_byte_format(schema)

        # Should be unchanged for 3.0.x
        data_prop = result["components"]["schemas"]["File"]["properties"]["data"]
        assert data_prop["format"] == "byte"
        assert "contentEncoding" not in data_prop

    def test_version_detection_31_variations(self):
        """Test that all 3.1.x versions trigger the conversion."""
        for version in ["3.1.0", "3.1.1", "3.1.2"]:
            schema = {
                "openapi": version,
                "components": {
                    "schemas": {
                        "Test": {
                            "type": "object",
                            "properties": {"file": {"type": "string", "format": "byte"}},
                        }
                    }
                },
            }

            result = fix_byte_format(schema)

            file_prop = result["components"]["schemas"]["Test"]["properties"]["file"]
            assert "format" not in file_prop
            assert file_prop["contentEncoding"] == "base64"

    def test_other_formats_unchanged(self):
        """Test that other format values are not modified."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "format": "email"},
                            "date": {"type": "string", "format": "date-time"},
                            "binary": {"type": "string", "format": "binary"},
                        },
                    }
                }
            },
        }

        result = fix_byte_format(schema)

        props = result["components"]["schemas"]["User"]["properties"]
        assert props["email"]["format"] == "email"
        assert props["date"]["format"] == "date-time"
        assert props["binary"]["format"] == "binary"

    def test_nested_format_byte_converted(self):
        """Test that nested format: byte is converted."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "Document": {
                        "type": "object",
                        "properties": {
                            "attachment": {
                                "type": "object",
                                "properties": {"content": {"type": "string", "format": "byte"}},
                            }
                        },
                    }
                }
            },
        }

        result = fix_byte_format(schema)

        document = result["components"]["schemas"]["Document"]
        attachment_props = document["properties"]["attachment"]["properties"]
        content_prop = attachment_props["content"]
        assert "format" not in content_prop
        assert content_prop["contentEncoding"] == "base64"

    def test_format_byte_in_array_items(self):
        """Test that format: byte in array items is converted."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "Files": {
                        "type": "object",
                        "properties": {
                            "attachments": {
                                "type": "array",
                                "items": {"type": "string", "format": "byte"},
                            }
                        },
                    }
                }
            },
        }

        result = fix_byte_format(schema)

        items_prop = result["components"]["schemas"]["Files"]["properties"]["attachments"]["items"]
        assert "format" not in items_prop
        assert items_prop["contentEncoding"] == "base64"

    def test_multiple_byte_formats_converted(self):
        """Test that multiple format: byte occurrences are all converted."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "Upload": {
                        "type": "object",
                        "properties": {
                            "file1": {"type": "string", "format": "byte"},
                            "file2": {"type": "string", "format": "byte"},
                            "text": {"type": "string"},
                        },
                    }
                }
            },
        }

        result = fix_byte_format(schema)

        props = result["components"]["schemas"]["Upload"]["properties"]
        assert props["file1"]["contentEncoding"] == "base64"
        assert "format" not in props["file1"]
        assert props["file2"]["contentEncoding"] == "base64"
        assert "format" not in props["file2"]
        assert "contentEncoding" not in props["text"]

    def test_preserves_other_properties(self):
        """Test that other properties are preserved during conversion."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "Attachment": {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "string",
                                "format": "byte",
                                "description": "Base64 encoded file data",
                                "example": "SGVsbG8gV29ybGQ=",
                            }
                        },
                    }
                }
            },
        }

        result = fix_byte_format(schema)

        data_prop = result["components"]["schemas"]["Attachment"]["properties"]["data"]
        assert data_prop["contentEncoding"] == "base64"
        assert data_prop["description"] == "Base64 encoded file data"
        assert data_prop["example"] == "SGVsbG8gV29ybGQ="
        assert "format" not in data_prop

    def test_non_string_type_with_byte_format_unchanged(self):
        """Test that non-string types with format: byte are not modified."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "Test": {
                        "type": "object",
                        "properties": {
                            "weird": {
                                "type": "integer",
                                # Invalid but we should not crash
                                "format": "byte",
                            }
                        },
                    }
                }
            },
        }

        result = fix_byte_format(schema)

        # Should be unchanged (we only convert string types)
        weird_prop = result["components"]["schemas"]["Test"]["properties"]["weird"]
        assert weird_prop["format"] == "byte"
        assert "contentEncoding" not in weird_prop

    def test_schema_without_format_unchanged(self):
        """Test that schemas without format are unchanged."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {"User": {"type": "object", "properties": {"name": {"type": "string"}}}}
            },
        }

        expected = schema.copy()

        result = fix_byte_format(schema)
        assert result == expected
