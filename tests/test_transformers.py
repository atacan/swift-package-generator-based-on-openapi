"""Tests for OpenAPI transformation operations."""

from bootstrapper.transformers.op1_null_anyof import remove_null_anyof
from bootstrapper.transformers.op2_const_enum import convert_const_to_enum
from bootstrapper.transformers.op3_nullable import convert_nullable_to_3_1
from bootstrapper.transformers.op4_format_fix import fix_byte_format
from bootstrapper.transformers.op5_clean_required import clean_required_arrays


class TestOp1NullAnyOfRemoval:
    """Tests for Operation 1: Remove null from anyOf arrays."""

    def test_anyof_with_null_removed(self):
        """Test that type: null is removed from anyOf arrays."""
        schema = {
            "type": "object",
            "properties": {"username": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
        }

        expected = {"type": "object", "properties": {"username": {"type": "string"}}}

        result = remove_null_anyof(schema)
        assert result == expected

    def test_anyof_with_null_and_multiple_types(self):
        """Test anyOf with null and multiple other types."""
        schema = {
            "type": "object",
            "properties": {
                "value": {"anyOf": [{"type": "string"}, {"type": "number"}, {"type": "null"}]}
            },
        }

        expected = {
            "type": "object",
            "properties": {"value": {"anyOf": [{"type": "string"}, {"type": "number"}]}},
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_anyof_unwrapped_when_one_item_left(self):
        """Test that anyOf is unwrapped when only 1 item remains after removing null."""
        schema = {
            "type": "object",
            "properties": {
                "email": {"anyOf": [{"type": "string", "format": "email"}, {"type": "null"}]}
            },
        }

        expected = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email"}},
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_default_null_removed_when_type_no_longer_nullable(self):
        """Test that default: null is removed when type is no longer nullable."""
        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "anyOf": [{"type": "string", "enum": ["active", "inactive"]}, {"type": "null"}],
                    "default": None,
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["active", "inactive"]}},
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_default_null_kept_when_still_nullable(self):
        """Test that default: null is kept when type remains nullable via anyOf."""
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "anyOf": [{"type": "string"}, {"type": "number"}, {"type": "null"}],
                    "default": None,
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "data": {"anyOf": [{"type": "string"}, {"type": "number"}], "default": None}
            },
        }

        result = remove_null_anyof(schema)
        # anyOf still has multiple types, but null removed
        # default: null should be removed as type is no longer explicitly nullable
        expected["properties"]["data"].pop("default")
        assert result == expected

    def test_nested_anyof_processed(self):
        """Test that nested anyOf structures are processed correctly."""
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"inner": {"anyOf": [{"type": "boolean"}, {"type": "null"}]}},
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "nested": {"type": "object", "properties": {"inner": {"type": "boolean"}}}
            },
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_anyof_without_null_unchanged(self):
        """Test that anyOf without null type is unchanged."""
        schema = {
            "type": "object",
            "properties": {"multi": {"anyOf": [{"type": "string"}, {"type": "number"}]}},
        }

        expected = schema.copy()

        result = remove_null_anyof(schema)
        assert result == expected

    def test_anyof_only_null_becomes_null_type(self):
        """Test that anyOf with only null becomes a null type."""
        schema = {"type": "object", "properties": {"nullable_only": {"anyOf": [{"type": "null"}]}}}

        expected = {"type": "object", "properties": {"nullable_only": {"type": "null"}}}

        result = remove_null_anyof(schema)
        assert result == expected

    def test_complex_schema_with_multiple_anyof(self):
        """Test a complex schema with multiple anyOf occurrences."""
        schema = {
            "type": "object",
            "properties": {
                "field1": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
                "field2": {
                    "type": "array",
                    "items": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                },
                "field3": {
                    "anyOf": [
                        {"type": "object", "properties": {"name": {"type": "string"}}},
                        {"type": "null"},
                    ]
                },
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "array", "items": {"type": "integer"}},
                "field3": {"type": "object", "properties": {"name": {"type": "string"}}},
            },
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_preserves_other_properties(self):
        """Test that other properties are preserved during transformation."""
        schema = {
            "type": "object",
            "properties": {
                "title": {
                    "anyOf": [
                        {"type": "string", "minLength": 1, "maxLength": 100},
                        {"type": "null"},
                    ],
                    "description": "The title field",
                    "example": "Example Title",
                }
            },
            "required": ["title"],
        }

        expected = {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "The title field",
                    "example": "Example Title",
                }
            },
            "required": ["title"],
        }

        result = remove_null_anyof(schema)
        assert result == expected


class TestOp2ConstToEnum:
    """Tests for Operation 2: Convert const to enum."""

    def test_const_string_converted_to_enum(self):
        """Test that const with string value is converted to enum."""
        schema = {"type": "object", "properties": {"status": {"type": "string", "const": "active"}}}

        expected = {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["active"]}},
        }

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_const_number_converted_to_enum(self):
        """Test that const with number value is converted to enum."""
        schema = {"type": "object", "properties": {"version": {"type": "number", "const": 1.0}}}

        expected = {"type": "object", "properties": {"version": {"type": "number", "enum": [1.0]}}}

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_const_integer_converted_to_enum(self):
        """Test that const with integer value is converted to enum."""
        schema = {"type": "object", "properties": {"count": {"type": "integer", "const": 42}}}

        expected = {"type": "object", "properties": {"count": {"type": "integer", "enum": [42]}}}

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_const_boolean_converted_to_enum(self):
        """Test that const with boolean value is converted to enum."""
        schema = {"type": "object", "properties": {"enabled": {"type": "boolean", "const": True}}}

        expected = {
            "type": "object",
            "properties": {"enabled": {"type": "boolean", "enum": [True]}},
        }

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_const_null_converted_to_enum(self):
        """Test that const with null value is converted to enum."""
        schema = {"type": "object", "properties": {"value": {"const": None}}}

        expected = {"type": "object", "properties": {"value": {"enum": [None]}}}

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_const_key_removed(self):
        """Test that const key is removed after conversion."""
        schema = {
            "type": "object",
            "properties": {"literal": {"type": "string", "const": "fixed_value"}},
        }

        result = convert_const_to_enum(schema)
        assert "const" not in result["properties"]["literal"]
        assert "enum" in result["properties"]["literal"]

    def test_nested_const_converted(self):
        """Test that nested const values are converted."""
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"inner": {"type": "string", "const": "nested_value"}},
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"inner": {"type": "string", "enum": ["nested_value"]}},
                }
            },
        }

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_const_in_array_items_converted(self):
        """Test that const in array items is converted."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string", "const": "fixed_tag"}}
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string", "enum": ["fixed_tag"]}}
            },
        }

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_multiple_const_values_converted(self):
        """Test that multiple const values in different properties are converted."""
        schema = {
            "type": "object",
            "properties": {
                "field1": {"type": "string", "const": "value1"},
                "field2": {"type": "number", "const": 123},
                "field3": {"type": "boolean", "const": False},
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "field1": {"type": "string", "enum": ["value1"]},
                "field2": {"type": "number", "enum": [123]},
                "field3": {"type": "boolean", "enum": [False]},
            },
        }

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_preserves_other_properties(self):
        """Test that other properties are preserved during transformation."""
        schema = {
            "type": "object",
            "properties": {
                "api_version": {
                    "type": "string",
                    "const": "v1",
                    "description": "API version identifier",
                    "example": "v1",
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "api_version": {
                    "type": "string",
                    "enum": ["v1"],
                    "description": "API version identifier",
                    "example": "v1",
                }
            },
        }

        result = convert_const_to_enum(schema)
        assert result == expected

    def test_schema_without_const_unchanged(self):
        """Test that schemas without const are unchanged."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string", "enum": ["option1", "option2"]}},
        }

        expected = schema.copy()

        result = convert_const_to_enum(schema)
        assert result == expected


class TestOp3NullableTo31:
    """Tests for Operation 3: Handle nullable properties for Swift OpenAPI Generator."""

    def test_nullable_string_removed_from_required(self):
        """Test that nullable: true removes property from required array."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {"name": {"type": "string", "nullable": True}},
                    }
                }
            },
        }

        result = convert_nullable_to_3_1(schema)

        # Check that nullable was removed
        assert "nullable" not in result["components"]["schemas"]["User"]["properties"]["name"]
        # Check that type is still string (not array)
        assert result["components"]["schemas"]["User"]["properties"]["name"]["type"] == "string"
        # Check that required array is empty or removed
        assert "required" not in result["components"]["schemas"]["User"] or result["components"]["schemas"]["User"]["required"] == []

    def test_nullable_number_removed_from_required(self):
        """Test that nullable number is removed from required array."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "Product": {
                        "type": "object",
                        "required": ["name", "price"],
                        "properties": {
                            "name": {"type": "string"},
                            "price": {"type": "number", "nullable": True}
                        },
                    }
                }
            },
        }

        result = convert_nullable_to_3_1(schema)

        price_prop = result["components"]["schemas"]["Product"]["properties"]["price"]
        assert "nullable" not in price_prop
        assert price_prop["type"] == "number"
        # Only name should remain in required
        assert result["components"]["schemas"]["Product"]["required"] == ["name"]

    def test_nullable_false_removed_but_stays_required(self):
        """Test that nullable: false is removed but property stays in required."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "Item": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {"id": {"type": "string", "nullable": False}},
                    }
                }
            },
        }

        result = convert_nullable_to_3_1(schema)

        id_prop = result["components"]["schemas"]["Item"]["properties"]["id"]
        assert "nullable" not in id_prop
        assert id_prop["type"] == "string"  # Remains a simple string
        # Should stay in required since nullable: false
        assert result["components"]["schemas"]["Item"]["required"] == ["id"]

    def test_openapi_31_spec_also_processed(self):
        """Test that OpenAPI 3.1+ specs are also processed (we clean all specs)."""
        schema = {
            "openapi": "3.1.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {
                                "type": ["string", "null"],
                            }
                        },
                    }
                }
            },
        }

        result = convert_nullable_to_3_1(schema)

        # Type array should be unwrapped and removed from required
        name_prop = result["components"]["schemas"]["User"]["properties"]["name"]
        assert name_prop["type"] == "string"
        assert "required" not in result["components"]["schemas"]["User"] or result["components"]["schemas"]["User"]["required"] == []

    def test_version_detection_all_versions(self):
        """Test that all OpenAPI versions are handled consistently."""
        for version in ["3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.1.0"]:
            schema = {
                "openapi": version,
                "components": {
                    "schemas": {
                        "Test": {
                            "type": "object",
                            "required": ["field"],
                            "properties": {"field": {"type": "string", "nullable": True}},
                        }
                    }
                },
            }

            result = convert_nullable_to_3_1(schema)

            # Should be processed for all versions
            field_prop = result["components"]["schemas"]["Test"]["properties"]["field"]
            assert "nullable" not in field_prop
            assert field_prop["type"] == "string"
            # Should be removed from required
            assert "required" not in result["components"]["schemas"]["Test"] or result["components"]["schemas"]["Test"]["required"] == []

    def test_nested_nullable_properties(self):
        """Test that nested nullable properties are handled correctly."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "Address": {
                        "type": "object",
                        "required": ["street"],
                        "properties": {
                            "street": {"type": "string", "nullable": True},
                            "details": {
                                "type": "object",
                                "required": ["apartment"],
                                "properties": {"apartment": {"type": "string", "nullable": True}},
                            },
                        },
                    }
                }
            },
        }

        result = convert_nullable_to_3_1(schema)

        address = result["components"]["schemas"]["Address"]["properties"]
        assert address["street"]["type"] == "string"
        assert "nullable" not in address["street"]
        # street should be removed from required
        assert "required" not in result["components"]["schemas"]["Address"] or result["components"]["schemas"]["Address"]["required"] == []

        details = address["details"]["properties"]
        assert details["apartment"]["type"] == "string"
        assert "nullable" not in details["apartment"]
        # apartment should be removed from required in nested object
        assert "required" not in address["details"] or address["details"]["required"] == []

    def test_nullable_with_other_properties_preserved(self):
        """Test that other properties are preserved during conversion."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "required": ["email"],
                        "properties": {
                            "email": {
                                "type": "string",
                                "format": "email",
                                "nullable": True,
                                "description": "User email address",
                                "example": "user@example.com",
                            }
                        },
                    }
                }
            },
        }

        result = convert_nullable_to_3_1(schema)

        email_prop = result["components"]["schemas"]["User"]["properties"]["email"]
        assert email_prop["type"] == "string"
        assert email_prop["format"] == "email"
        assert email_prop["description"] == "User email address"
        assert email_prop["example"] == "user@example.com"
        assert "nullable" not in email_prop
        # Should be removed from required
        assert "required" not in result["components"]["schemas"]["User"] or result["components"]["schemas"]["User"]["required"] == []

    def test_nullable_in_array_items(self):
        """Test that nullable in array items is cleaned."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "List": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {"type": "string", "nullable": True},
                            }
                        },
                    }
                }
            },
        }

        result = convert_nullable_to_3_1(schema)

        items_schema = result["components"]["schemas"]["List"]["properties"]["items"]["items"]
        assert items_schema["type"] == "string"
        assert "nullable" not in items_schema

    def test_multiple_nullable_properties(self):
        """Test that multiple nullable properties are all handled."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "required": ["name", "age", "active"],
                        "properties": {
                            "name": {"type": "string", "nullable": True},
                            "age": {"type": "integer", "nullable": True},
                            "active": {"type": "boolean", "nullable": True},
                        },
                    }
                }
            },
        }

        result = convert_nullable_to_3_1(schema)

        props = result["components"]["schemas"]["User"]["properties"]
        assert props["name"]["type"] == "string"
        assert props["age"]["type"] == "integer"
        assert props["active"]["type"] == "boolean"
        # All should be removed from required
        assert "required" not in result["components"]["schemas"]["User"] or result["components"]["schemas"]["User"]["required"] == []

    def test_schema_without_nullable_unchanged(self):
        """Test that schemas without nullable are unchanged."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {"id": {"type": "string"}}
                    }
                }
            },
        }

        expected = schema.copy()

        result = convert_nullable_to_3_1(schema)
        assert result == expected

    def test_mixed_nullable_and_required_properties(self):
        """Test schemas with mix of nullable and non-nullable required properties."""
        schema = {
            "components": {
                "schemas": {
                    "Test": {
                        "type": "object",
                        "required": ["id", "name", "email"],
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string", "nullable": True},
                            "email": {"type": "string"}
                        },
                    }
                }
            }
        }

        result = convert_nullable_to_3_1(schema)

        # name should be removed from required, but id and email should remain
        field_prop = result["components"]["schemas"]["Test"]["properties"]["name"]
        assert field_prop["type"] == "string"
        assert "nullable" not in field_prop
        assert result["components"]["schemas"]["Test"]["required"] == ["id", "email"]


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


class TestOp5CleanRequired:
    """Tests for Operation 5: Clean required arrays to match properties."""

    def test_remove_nonexistent_required_properties(self):
        """Test that required properties not in properties are removed."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "required": ["name", "email", "phone", "address"],
        }

        result = clean_required_arrays(schema)

        assert result["required"] == ["name", "email"]

    def test_all_required_exist_unchanged(self):
        """Test that required array is unchanged when all properties exist."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["id", "name"],
        }

        result = clean_required_arrays(schema)

        assert result["required"] == ["id", "name"]

    def test_empty_required_array_removed(self):
        """Test that empty required arrays are removed."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["id", "email"],  # None of these exist
        }

        result = clean_required_arrays(schema)

        # Empty required array should be removed
        assert "required" not in result or result["required"] == []

    def test_nested_schema_objects_processed(self):
        """Test that nested schema objects have their required arrays cleaned."""
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name", "email", "phone"],
                }
            },
        }

        result = clean_required_arrays(schema)

        user_required = result["properties"]["user"]["required"]
        assert user_required == ["name"]

    def test_deeply_nested_schemas(self):
        """Test that deeply nested schemas are all processed."""
        schema = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "level2": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name", "invalid"],
                        }
                    },
                    "required": ["level2", "other"],
                }
            },
            "required": ["level1", "missing"],
        }

        result = clean_required_arrays(schema)

        assert result["required"] == ["level1"]
        assert result["properties"]["level1"]["required"] == ["level2"]
        assert result["properties"]["level1"]["properties"]["level2"]["required"] == ["name"]

    def test_schema_without_properties_unchanged(self):
        """Test that schemas without properties have required removed or unchanged."""
        schema = {"type": "object", "required": ["something"]}

        result = clean_required_arrays(schema)

        # Required should be removed or empty since there are no properties
        assert "required" not in result or result["required"] == []

    def test_schema_without_required_unchanged(self):
        """Test that schemas without required are unchanged."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        expected = schema.copy()

        result = clean_required_arrays(schema)
        assert result == expected

    def test_array_items_with_required_processed(self):
        """Test that array items with required are processed."""
        schema = {
            "type": "object",
            "properties": {
                "users": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                        "required": ["id", "name"],
                    },
                }
            },
        }

        result = clean_required_arrays(schema)

        items_required = result["properties"]["users"]["items"]["required"]
        assert items_required == ["id"]

    def test_components_schemas_processed(self):
        """Test that schemas in components are processed."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name", "email", "id"],
                    },
                    "Product": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}, "price": {"type": "number"}},
                        "required": ["title", "price", "category"],
                    },
                }
            },
        }

        result = clean_required_arrays(schema)

        user_required = result["components"]["schemas"]["User"]["required"]
        assert user_required == ["name"]

        product_required = result["components"]["schemas"]["Product"]["required"]
        assert product_required == ["title", "price"]

    def test_preserves_order_of_required(self):
        """Test that the order of valid required properties is preserved."""
        schema = {
            "type": "object",
            "properties": {
                "a": {"type": "string"},
                "b": {"type": "string"},
                "c": {"type": "string"},
            },
            "required": ["c", "invalid1", "a", "invalid2", "b"],
        }

        result = clean_required_arrays(schema)

        assert result["required"] == ["c", "a", "b"]

    def test_multiple_schemas_at_same_level(self):
        """Test that multiple schemas at the same level are all processed."""
        schema = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {"type": {"type": "string"}},
                    "required": ["type", "missing1"],
                },
                {
                    "type": "object",
                    "properties": {"kind": {"type": "string"}},
                    "required": ["kind", "missing2"],
                },
            ]
        }

        result = clean_required_arrays(schema)

        assert result["oneOf"][0]["required"] == ["type"]
        assert result["oneOf"][1]["required"] == ["kind"]
