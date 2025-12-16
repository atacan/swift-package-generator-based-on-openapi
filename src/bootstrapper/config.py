"""Configuration constants and enums for the OpenAPI bootstrapper."""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

CONFIG_FILENAME = ".swift-bootstrapper.yaml"


class FileFormat(Enum):
    """Enum representing the format of an OpenAPI specification file."""

    JSON = "json"
    YAML = "yaml"


class ProjectConfig(BaseModel):
    """Configuration model for the Swift bootstrapper."""

    package_name: str | None = Field(default=None, description="Name of the Swift package")


def get_config_path(target_dir: Path) -> Path:
    """Get the path to the config file in the target directory."""
    return target_dir / CONFIG_FILENAME


def load_config(target_dir: Path) -> ProjectConfig:
    """
    Load configuration from .swift-bootstrapper.yaml file.
    Returns empty config if file doesn't exist.
    """
    config_path = get_config_path(target_dir)
    if not config_path.exists():
        return ProjectConfig()
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return ProjectConfig(**data)


def save_config(target_dir: Path, config: ProjectConfig) -> bool:
    """
    Save configuration to .swift-bootstrapper.yaml file.
    Only writes if file doesn't exist (preserves user edits).
    Returns True if created, False if already existed.
    """
    config_path = get_config_path(target_dir)
    if config_path.exists():
        return False
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(exclude_none=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return True


@dataclass
class NameMismatch:
    """Information about a package name mismatch."""

    config_name: str
    package_swift_name: str


def get_package_name_from_swift(target_dir: Path) -> str | None:
    """
    Extract package name from Package.swift file.

    Looks for: name: "PackageName"

    Returns None if file doesn't exist or name can't be parsed.
    """
    package_swift = target_dir / "Package.swift"
    if not package_swift.exists():
        return None

    content = package_swift.read_text(encoding="utf-8")
    # Match: name: "PackageName" with optional whitespace
    match = re.search(r'name:\s*"([^"]+)"', content)
    return match.group(1) if match else None


def check_name_mismatch(target_dir: Path, resolved_name: str) -> NameMismatch | None:
    """
    Check if resolved name differs from existing Package.swift.

    Returns NameMismatch if Package.swift exists with a different name,
    None otherwise.
    """
    existing_name = get_package_name_from_swift(target_dir)
    if existing_name is None:
        return None  # No Package.swift yet
    if existing_name == resolved_name:
        return None  # Names match
    return NameMismatch(config_name=resolved_name, package_swift_name=existing_name)
