"""Module for loading OpenAPI specification files."""

import json
from pathlib import Path

import yaml

from bootstrapper.config import FileFormat


def load_spec(path: Path) -> tuple[dict, FileFormat]:
    """
    Load an OpenAPI specification from a JSON or YAML file.

    Args:
        path: Path to the OpenAPI specification file (.json, .yaml, or .yml)

    Returns:
        A tuple of (parsed_dict, FileFormat) where:
        - parsed_dict is the OpenAPI spec as a Python dictionary
        - FileFormat indicates whether it was JSON or YAML

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file extension is not .json, .yaml, or .yml
        json.JSONDecodeError: If JSON parsing fails
        yaml.YAMLError: If YAML parsing fails
    """
    if not path.exists():
        raise FileNotFoundError(f"OpenAPI file not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data, FileFormat.JSON

    elif suffix in (".yaml", ".yml"):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data, FileFormat.YAML

    else:
        raise ValueError(f"Unsupported file format: {suffix}. Expected .json, .yaml, or .yml")
