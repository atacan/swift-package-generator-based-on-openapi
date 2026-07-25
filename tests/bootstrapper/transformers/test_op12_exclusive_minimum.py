"""Tests for op12_exclusive_minimum: normalize OpenAPI 3.0 minimum syntax."""

from pathlib import Path

import yaml

from bootstrapper.transformers.op12_exclusive_minimum import normalize_exclusive_minimum

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "history" / "exclusiveMinimum_problem_examples.yaml"
)


def _find_exclusive_minimum_values(data: object) -> list[object]:
    if isinstance(data, dict):
        values = [data["exclusiveMinimum"]] if "exclusiveMinimum" in data else []
        return values + [
            value for child in data.values() for value in _find_exclusive_minimum_values(child)
        ]
    if isinstance(data, list):
        return [value for child in data for value in _find_exclusive_minimum_values(child)]
    return []


def _find_boolean_exclusive_minimum_nodes(data: object) -> list[dict]:
    if isinstance(data, dict):
        nodes = [data] if data.get("exclusiveMinimum") is True else []
        return nodes + [
            node for child in data.values() for node in _find_boolean_exclusive_minimum_nodes(child)
        ]
    if isinstance(data, list):
        return [node for child in data for node in _find_boolean_exclusive_minimum_nodes(child)]
    return []


def _find_nodes_with_both_minimum_keywords(data: object) -> list[dict]:
    if isinstance(data, dict):
        nodes = [data] if {"minimum", "exclusiveMinimum"} <= data.keys() else []
        return nodes + [
            node
            for child in data.values()
            for node in _find_nodes_with_both_minimum_keywords(child)
        ]
    if isinstance(data, list):
        return [node for child in data for node in _find_nodes_with_both_minimum_keywords(child)]
    return []


def test_boolean_exclusive_minimum_is_normalized_at_all_fixture_levels():
    """Convert every nested 3.0-style boundary from the supplied example."""
    schemas = yaml.safe_load(FIXTURE_PATH.read_text())
    spec = {"openapi": "3.1.0", "components": {"schemas": schemas}}

    result = normalize_exclusive_minimum(spec)

    assert _find_exclusive_minimum_values(result) == [0, 0, 0, 0, 1.0e-05, 0, 0]
    assert _find_boolean_exclusive_minimum_nodes(result) == []
    assert _find_nodes_with_both_minimum_keywords(result) == []


def test_openapi_3_0_spec_is_unchanged():
    spec = {
        "openapi": "3.0.3",
        "components": {"schemas": {"PositiveNumber": {"minimum": 0, "exclusiveMinimum": True}}},
    }

    result = normalize_exclusive_minimum(spec)

    assert result["components"]["schemas"]["PositiveNumber"] == {
        "minimum": 0,
        "exclusiveMinimum": True,
    }


def test_numeric_exclusive_minimum_is_unchanged():
    spec = {
        "openapi": "3.1.0",
        "components": {"schemas": {"PositiveNumber": {"exclusiveMinimum": 0, "minimum": -1}}},
    }

    result = normalize_exclusive_minimum(spec)

    assert result["components"]["schemas"]["PositiveNumber"] == {
        "exclusiveMinimum": 0,
        "minimum": -1,
    }
