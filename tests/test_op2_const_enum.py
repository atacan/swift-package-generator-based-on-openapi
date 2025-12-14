"""Tests for Operation 2: Convert const to enum."""

from bootstrapper.transformers.op2_const_enum import convert_const_to_enum


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
