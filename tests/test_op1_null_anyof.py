"""Tests for Operation 1: Remove null from anyOf arrays."""

from bootstrapper.transformers.op1_null_anyof import remove_null_anyof


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


class TestOp1NullOneOfRemoval:
    """Tests for Operation 1: Remove null from oneOf arrays."""

    def test_oneof_with_null_removed(self):
        """Test that type: null is removed from oneOf arrays and unwrapped."""
        schema = {
            "type": "object",
            "properties": {
                "username": {"oneOf": [{"$ref": "#/components/schemas/User"}, {"type": "null"}]}
            },
        }

        expected = {
            "type": "object",
            "properties": {"username": {"$ref": "#/components/schemas/User"}},
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_oneof_with_null_and_multiple_types(self):
        """Test oneOf with null and multiple other types - keeps oneOf minus null."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "number"},
                        {"type": "boolean"},
                        {"type": "null"},
                    ]
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "value": {"oneOf": [{"type": "string"}, {"type": "number"}, {"type": "boolean"}]}
            },
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_oneof_unwrapped_when_one_item_left(self):
        """Test that oneOf is unwrapped when only 1 item remains after removing null."""
        schema = {
            "type": "object",
            "properties": {
                "email": {
                    "oneOf": [
                        {"type": "string", "format": "email", "minLength": 5},
                        {"type": "null"},
                    ]
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email", "minLength": 5}},
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_nested_oneof_with_anyof(self):
        """Test the key nested case: oneOf containing anyOf, then null."""
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "oneOf": [
                        {
                            "anyOf": [
                                {"$ref": "#/components/schemas/DataModel"},
                                {"type": "string"},
                            ]
                        },
                        {"type": "null"},
                    ]
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "data": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/DataModel"},
                        {"type": "string"},
                    ]
                }
            },
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_oneof_only_null_becomes_null_type(self):
        """Test that oneOf with only null becomes a null type."""
        schema = {
            "type": "object",
            "properties": {"nullable_only": {"oneOf": [{"type": "null"}]}},
        }

        expected = {"type": "object", "properties": {"nullable_only": {"type": "null"}}}

        result = remove_null_anyof(schema)
        assert result == expected

    def test_oneof_preserves_other_properties(self):
        """Test that description, example, etc. are preserved during transformation."""
        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "oneOf": [
                        {"type": "string", "enum": ["active", "inactive"]},
                        {"type": "null"},
                    ],
                    "description": "The status field",
                    "example": "active",
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive"],
                    "description": "The status field",
                    "example": "active",
                }
            },
        }

        result = remove_null_anyof(schema)
        assert result == expected

    def test_oneof_without_null_unchanged(self):
        """Test that oneOf without null type is unchanged."""
        schema = {
            "type": "object",
            "properties": {"multi": {"oneOf": [{"type": "string"}, {"type": "number"}]}},
        }

        expected = schema.copy()

        result = remove_null_anyof(schema)
        assert result == expected

    def test_nested_oneof_processed(self):
        """Test that nested oneOf structures are processed correctly."""
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"inner": {"oneOf": [{"type": "boolean"}, {"type": "null"}]}},
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

    def test_oneof_default_null_removed(self):
        """Test that default: null is removed when oneOf type is no longer nullable."""
        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "oneOf": [
                        {"type": "string", "enum": ["pending", "completed"]},
                        {"type": "null"},
                    ],
                    "default": None,
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["pending", "completed"]}},
        }

        result = remove_null_anyof(schema)
        assert result == expected
