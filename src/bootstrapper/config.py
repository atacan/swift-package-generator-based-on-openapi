"""Configuration constants and enums for the OpenAPI bootstrapper."""

from enum import Enum


class FileFormat(Enum):
    """Enum representing the format of an OpenAPI specification file."""

    JSON = "json"
    YAML = "yaml"
