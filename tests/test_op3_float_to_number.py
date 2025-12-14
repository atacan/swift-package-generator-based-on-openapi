"""Tests for Operation 3: Convert type: float to type: number."""

from bootstrapper.transformers.op3_float_to_number import convert_float_to_number


class TestOp3FloatToNumber:
    """Tests for Operation 3: Convert type: float to type: number."""

    def test_float_converted_to_number_with_format(self):
        """Test that type: float is converted to type: number with format: float."""
        schema = {"type": "object", "properties": {"price": {"type": "float"}}}

        expected = {
            "type": "object",
            "properties": {"price": {"type": "number", "format": "float"}},
        }

        result = convert_float_to_number(schema)
        assert result == expected

    def test_float_key_removed(self):
        """Test that type: float is replaced with type: number."""
        schema = {
            "type": "object",
            "properties": {"value": {"type": "float"}},
        }

        result = convert_float_to_number(schema)
        assert result["properties"]["value"]["type"] == "number"
        assert result["properties"]["value"]["format"] == "float"

    def test_nested_float_converted(self):
        """Test that nested float types are converted."""
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"inner_value": {"type": "float"}},
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"inner_value": {"type": "number", "format": "float"}},
                }
            },
        }

        result = convert_float_to_number(schema)
        assert result == expected

    def test_float_in_array_items_converted(self):
        """Test that float in array items is converted."""
        schema = {
            "type": "object",
            "properties": {"coordinates": {"type": "array", "items": {"type": "float"}}},
        }

        expected = {
            "type": "object",
            "properties": {
                "coordinates": {"type": "array", "items": {"type": "number", "format": "float"}}
            },
        }

        result = convert_float_to_number(schema)
        assert result == expected

    def test_multiple_float_values_converted(self):
        """Test that multiple float types in different properties are converted."""
        schema = {
            "type": "object",
            "properties": {
                "latitude": {"type": "float"},
                "longitude": {"type": "float"},
                "altitude": {"type": "float"},
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "format": "float"},
                "longitude": {"type": "number", "format": "float"},
                "altitude": {"type": "number", "format": "float"},
            },
        }

        result = convert_float_to_number(schema)
        assert result == expected

    def test_preserves_other_properties(self):
        """Test that other properties are preserved during transformation."""
        schema = {
            "type": "object",
            "properties": {
                "temperature": {
                    "type": "float",
                    "description": "Temperature in Celsius",
                    "example": 23.5,
                    "minimum": -273.15,
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "temperature": {
                    "type": "number",
                    "format": "float",
                    "description": "Temperature in Celsius",
                    "example": 23.5,
                    "minimum": -273.15,
                }
            },
        }

        result = convert_float_to_number(schema)
        assert result == expected

    def test_schema_without_float_unchanged(self):
        """Test that schemas without float types are unchanged."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "is_active": {"type": "boolean"},
            },
        }

        expected = schema.copy()

        result = convert_float_to_number(schema)
        assert result == expected

    def test_float_in_oneof_converted(self):
        """Test that float types within oneOf are converted."""
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "float"},
                        {"type": "string"},
                    ]
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "number", "format": "float"},
                        {"type": "string"},
                    ]
                }
            },
        }

        result = convert_float_to_number(schema)
        assert result == expected

    def test_float_in_anyof_converted(self):
        """Test that float types within anyOf are converted."""
        schema = {
            "type": "object",
            "properties": {
                "measurement": {
                    "anyOf": [
                        {"type": "float", "description": "Metric value"},
                        {"type": "integer", "description": "Imperial value"},
                    ]
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "measurement": {
                    "anyOf": [
                        {"type": "number", "format": "float", "description": "Metric value"},
                        {"type": "integer", "description": "Imperial value"},
                    ]
                }
            },
        }

        result = convert_float_to_number(schema)
        assert result == expected

    def test_float_in_allof_converted(self):
        """Test that float types within allOf are converted."""
        schema = {
            "type": "object",
            "properties": {
                "composite": {
                    "allOf": [
                        {"type": "float"},
                        {"minimum": 0.0, "maximum": 100.0},
                    ]
                }
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "composite": {
                    "allOf": [
                        {"type": "number", "format": "float"},
                        {"minimum": 0.0, "maximum": 100.0},
                    ]
                }
            },
        }

        result = convert_float_to_number(schema)
        assert result == expected
