"""Tests for Operation 3: Handle nullable properties for Swift OpenAPI Generator."""

from bootstrapper.transformers.op4_nullable import convert_nullable_to_3_1


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
        user_schema = result["components"]["schemas"]["User"]
        assert "required" not in user_schema or user_schema["required"] == []

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
                            "price": {"type": "number", "nullable": True},
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
        user_schema = result["components"]["schemas"]["User"]
        assert "required" not in user_schema or user_schema["required"] == []

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
            test_schema = result["components"]["schemas"]["Test"]
            assert "required" not in test_schema or test_schema["required"] == []

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
        addr_schema = result["components"]["schemas"]["Address"]
        assert "required" not in addr_schema or addr_schema["required"] == []

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
        user_schema = result["components"]["schemas"]["User"]
        assert "required" not in user_schema or user_schema["required"] == []

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
        user_schema = result["components"]["schemas"]["User"]
        assert "required" not in user_schema or user_schema["required"] == []

    def test_schema_without_nullable_unchanged(self):
        """Test that schemas without nullable are unchanged."""
        schema = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {"id": {"type": "string"}},
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
                            "email": {"type": "string"},
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
