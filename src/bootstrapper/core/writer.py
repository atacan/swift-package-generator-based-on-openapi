"""Module for writing OpenAPI specification files."""

import json
from pathlib import Path

import yaml

from bootstrapper.config import FileFormat


class NoAliasDumper(yaml.SafeDumper):
    """
    Custom YAML dumper that disables alias/anchor generation.

    Swift's OpenAPI parser may not handle YAML aliases correctly,
    so we disable them to ensure compatibility.
    """

    def ignore_aliases(self, data):
        """Always return True to disable alias generation."""
        return True


def write_spec(data: dict, path: Path, format: FileFormat) -> None:
    """
    Write an OpenAPI specification to a JSON or YAML file.

    Args:
        data: The OpenAPI spec as a Python dictionary
        path: Path where the file should be written
        format: FileFormat indicating whether to write JSON or YAML

    Raises:
        ValueError: If an unsupported FileFormat is provided
        IOError: If writing to the file fails
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    if format == FileFormat.JSON:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add trailing newline

    elif format == FileFormat.YAML:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                Dumper=NoAliasDumper,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
            )

    else:
        raise ValueError(f"Unsupported file format: {format}")
