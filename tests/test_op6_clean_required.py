"""Tests for Operation 5: Clean required arrays to match properties."""

from bootstrapper.transformers.op6_clean_required import clean_required_arrays


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
